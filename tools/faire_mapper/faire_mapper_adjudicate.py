"""faire_mapper_adjudicate: answer the mapper's review requests with a language model.

Reads adjudication_requests.json from `faire_mapper.py map`, asks a model to choose a FAIRe term
for each column (or none), checks that every answer is one of the column's candidates, and writes
an answers file for `faire_mapper.py map --responses`.

The model only ever chooses from the candidates the mapper offers; any other answer is discarded.

Where the answers come from (one of):
  --model NAME             call a model: Claude (--api anthropic, the default; key in ANTHROPIC_API_KEY)
                           or any service that takes OpenAI's request format (--api openai: OpenAI,
                           LiteLLM gateways, vLLM, Ollama and others; key in OPENAI_API_KEY), at
                           --api_url if it is not the provider's public address
  --from_env PREFIX        the same, with every setting from environment variables: PREFIX_FORMAT
                           (anthropic or openai), PREFIX_URL, PREFIX_MODEL and PREFIX_KEY. The Galaxy
                           tool uses FAIRE_MAPPER_USER (the user's own service, from Galaxy's
                           credentials) or FAIRE_MAPPER_SERVER (a model the Galaxy server provides,
                           set in its job rules)
  --answers_from FILE      check answers produced elsewhere (a person, another model)
--dry_run writes the prompts that would be sent, without calling anything (with --model or
--from_env it also reports the service and model that would be used).

Keys are read from the environment only, never from the command line. Standard library only, so it
adds no dependencies.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API_URL = 'https://api.anthropic.com/v1/messages'
OPENAI_URL = 'https://api.openai.com/v1'
PUBLIC_URLS = {'anthropic': API_URL, 'openai': OPENAI_URL}
KEY_ENV = {'anthropic': 'ANTHROPIC_API_KEY', 'openai': 'OPENAI_API_KEY'}
DEFAULT_MODEL = 'claude-sonnet-5-5'
DEFAULT_API_VERSION = '2026-10-21'  # the current version (Claude API reference, November 2026)

SYSTEM = (
    "You help map columns of environmental DNA (eDNA) sample sheets to terms of the FAIRe metadata "
    "standard (FAIR eDNA, based on Darwin Core and MIxS). For one column you are given its header, "
    "the data provider's description of it when there is one, example values, a profile of its values, "
    "and candidate FAIRe terms with their descriptions, types and allowed values. Choose the candidate "
    "the column holds, judging from the header, the description and the values. If no candidate fits, "
    "answer null. Never answer a term that is not a candidate. "
    "Reply with one JSON object only: {\"column\": <header>, \"term\": <candidate term or null>, "
    "\"reason\": <one short sentence>}."
)


def prompt_for(req):
    body = {k: req[k] for k in ('column', 'description', 'values', 'profile', 'proposed', 'candidates') if k in req}
    return 'Column to map:\n' + json.dumps(body, ensure_ascii=False, indent=1)


def parse_reply(text):
    m = re.search(r'\{.*\}', text, re.S)
    if not m:
        raise ValueError('no JSON object in the reply')
    return json.loads(m.group(0))


def check(req, ans):
    """Return a cleaned answer, or None with a reason when the answer cannot be used."""
    allowed = {c['term'] for c in req.get('candidates', [])}
    if not isinstance(ans, dict):
        return None, 'answer is not a JSON object'
    if ans.get('column') not in (None, req['column']):
        return None, f"answer is for another column ({ans.get('column')!r})"
    term = ans.get('term')
    if isinstance(term, str) and term.strip().lower() in ('', 'null', 'none'):
        term = None
    if term is not None and term not in allowed:
        return None, f'term {term!r} is not one of the candidates'
    return {'column': req['column'], 'term': term, 'reason': str(ans.get('reason', ''))[:300]}, ''


class Fatal(Exception):
    """A problem that affects every request (no key, wrong address, unknown model): stop the run."""


def endpoint(api, url):
    """The address to post to: OpenAI's format adds /chat/completions to a service's base address
    (https://api.openai.com/v1); Anthropic's adds /messages (https://api.anthropic.com/v1)."""
    url = (url or PUBLIC_URLS[api]).rstrip('/')
    tail = '/chat/completions' if api == 'openai' else '/messages'
    return url if url.endswith(tail) else url + tail


def reply_text(api, out):
    if api == 'anthropic':
        return ''.join(b.get('text', '') for b in out.get('content', []) if b.get('type') == 'text')
    content = ((out.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
    if isinstance(content, list):  # some services return a list of parts
        content = ''.join(c.get('text', '') for c in content if isinstance(c, dict))
    return content


def call_model(req, model, api_key, api_version=DEFAULT_API_VERSION, timeout=60, retries=4, api_url=None,
               api='anthropic'):
    if api == 'anthropic':
        payload = {'model': model, 'max_tokens': 300, 'system': SYSTEM,
                   'messages': [{'role': 'user', 'content': prompt_for(req)}]}
        headers = {'content-type': 'application/json', 'anthropic-version': api_version}
        if api_key:
            headers['authorization'] = f'Bearer {api_key}'  # the main header; x-api-key is the legacy one
    else:
        # Only the model and the messages, which every service in this format accepts (some
        # models refuse a temperature or a token limit).
        payload = {'model': model, 'messages': [{'role': 'system', 'content': SYSTEM},
                                                {'role': 'user', 'content': prompt_for(req)}]}
        headers = {'content-type': 'application/json'}
        if api_key:
            headers['authorization'] = f'Bearer {api_key}'
    data = json.dumps(payload).encode()
    url = endpoint(api, api_url)
    for attempt in range(retries + 1):
        try:
            r = urllib.request.Request(url, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                out = json.loads(resp.read().decode())
            return parse_reply(reply_text(api, out))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 529) and attempt < retries:
                time.sleep(2 ** attempt * 2)
                continue
            body = e.read().decode(errors='replace')[:300]
            if e.code in (401, 403):
                raise Fatal(f'the model service refused the request ({e.code}): check the API key. {body}')
            if e.code == 404:
                raise Fatal(f'the model service answered 404: check its address ({url}) and the model '
                            f'name ({model}). {body}')
            raise RuntimeError(f'API error {e.code}: {body}')
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < min(retries, 2):
                time.sleep(2 ** attempt * 2)
                continue
            raise Fatal(f'could not reach the model service at {url} ({getattr(e, "reason", e)})')


def settings(args):
    """The service to call: request format, address, model and key."""
    if args.from_env:
        p = args.from_env
        get = lambda name: (os.environ.get(f'{p}_{name}') or '').strip()  # noqa: E731
        api = (get('FORMAT') or 'openai').lower()
        if api not in PUBLIC_URLS:
            raise Fatal(f"{p}_FORMAT is {api!r}; it should be openai or anthropic")
        url, model, key = get('URL') or None, get('MODEL'), get('KEY') or None
        if not model:
            if p.endswith('SERVER'):
                raise Fatal('this Galaxy server provides no language model for the FAIRe mapper. Choose '
                            'your own model service, or review the columns yourself.')
            raise Fatal('no model is set: give the model name in the credentials for this tool.')
    else:
        api, url, model = args.api, args.api_url, args.model
        if api == 'openai' and model == DEFAULT_MODEL:
            raise Fatal('give the model name with --model NAME when --api is openai')
        key = os.environ.get(KEY_ENV[api]) or None
    if not key and not url:
        where = 'in the credentials for this tool' if args.from_env else f'in {KEY_ENV[api]}'
        raise Fatal(f"no API key for {PUBLIC_URLS[api]}: give one {where}, or the address of a service "
                    'that needs none.')
    return {'api': api, 'url': url, 'model': model, 'key': key}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('requests', help='adjudication_requests.json from faire_mapper.py map')
    ap.add_argument('-o', '--output', required=True, help='answers file for faire_mapper.py map --responses')
    src = ap.add_mutually_exclusive_group()
    src.add_argument('--model', nargs='?', const=DEFAULT_MODEL,
                     help=f'model to call (default with --api anthropic: {DEFAULT_MODEL})')
    src.add_argument('--from_env', metavar='PREFIX',
                     help='read the format, address, model and key from PREFIX_FORMAT, PREFIX_URL, '
                          'PREFIX_MODEL and PREFIX_KEY')
    src.add_argument('--answers_from', help='JSON list of answers to check instead of calling a model')
    ap.add_argument('--dry_run', action='store_true', help='write the prompts only')
    ap.add_argument('--api', choices=['anthropic', 'openai'], default='anthropic',
                    help='request format of the service (with --model; default anthropic)')
    ap.add_argument('--api_url', help="the service's address, if not the provider's public one "
                                      '(for example http://localhost:11434/v1 for Ollama)')
    ap.add_argument('--api_version', default=DEFAULT_API_VERSION, help='anthropic-version header')
    ap.add_argument('--answered_by', default='person',
                    help='who gave the --answers_from answers: "person" (default), or "model:<name>" for a model; '
                         'the mapper only marks a person\'s answers as confirmed')
    ap.add_argument('--log', help='write a TSV of every request, answer and check result')
    args = ap.parse_args(argv)
    if not (args.model or args.from_env or args.answers_from or args.dry_run):
        ap.error('give --model, --from_env, --answers_from or --dry_run')

    reqs = json.load(open(args.requests))
    service = None
    if args.model or args.from_env:
        try:
            service = settings(args)
        except Fatal as e:
            if not args.dry_run:
                sys.stderr.write(f'ERROR: {e}\n')
                return 2
            print(f'INFO: no model service could be used: {e}')
    if args.dry_run:
        with open(args.output, 'w') as f:
            json.dump([{'system': SYSTEM, 'user': prompt_for(r)} for r in reqs], f, indent=1, ensure_ascii=False)
        print(f'INFO: wrote the {len(reqs)} prompts that would be sent; nothing was sent')
        if service:
            print(f"INFO: they would go to {endpoint(service['api'], service['url'])}, model {service['model']}, "
                  + ('with an API key' if service['key'] else 'without an API key'))
        return 0

    given = {}
    if args.answers_from:
        raw = json.load(open(args.answers_from))
        raw = raw.get('responses', raw) if isinstance(raw, dict) else raw
        given = {a.get('column'): a for a in raw if isinstance(a, dict)}
    else:
        print(f"INFO: asking {service['model']} at {endpoint(service['api'], service['url'])} about "
              f"{len(reqs)} column(s)")

    answers, log = [], []
    for req in reqs:
        try:
            ans = given.get(req['column']) if args.answers_from else call_model(
                req, service['model'], service['key'], args.api_version, api_url=service['url'], api=service['api'])
            if ans is None:
                cleaned, why = None, 'no answer given'
            else:
                cleaned, why = check(req, ans)
        except Fatal as e:
            sys.stderr.write(f'ERROR: {e}\n')
            return 1
        except (RuntimeError, ValueError) as e:
            cleaned, why, ans = None, str(e), None
        if cleaned:
            if args.answers_from:
                cleaned['by'] = str(ans.get('by') or args.answered_by)
            else:
                cleaned['by'] = f"model:{service['model']}"
            answers.append(cleaned)
        log.append({'column': req['column'], 'proposed': req.get('proposed') or '',
                    'answer': '' if not cleaned else (cleaned['term'] or 'null'),
                    'used': bool(cleaned), 'problem': why,
                    'reason': cleaned['reason'] if cleaned else ''})
    with open(args.output, 'w') as f:
        json.dump(answers, f, indent=1, ensure_ascii=False)
    if args.log:
        with open(args.log, 'w') as f:
            f.write('column\tproposed\tanswer\tused\tproblem\treason\n')
            for r in log:
                f.write('\t'.join(str(r[k]).replace('\t', ' ').replace('\n', ' ') for k in
                                  ('column', 'proposed', 'answer', 'used', 'problem', 'reason')) + '\n')
    bad = sum(not r['used'] for r in log)
    print(f'INFO: {len(answers)} of {len(reqs)} answers usable; {bad} discarded')
    return 0


if __name__ == '__main__':
    sys.exit(main())
