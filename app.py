from flask import Flask, render_template, jsonify, request
import requests
import json
from datetime import datetime

app = Flask(__name__)

# Load configuration
try:
    with open('token.json', 'r') as f:
        config = json.load(f)
        API_TOKEN = config.get('token', '')
except Exception as e:
    print(f"Error loading token.json: {e}")
    API_TOKEN = ''

try:
    with open('project.json', 'r') as f:
        project_config = json.load(f)
        API_BASE_URL = project_config.get('api_base_url', 'https://demo.defectdojo.org')
except Exception as e:
    print(f"Error loading project.json: {e}")
    API_BASE_URL = 'https://demo.defectdojo.org'

HEADERS = {
    'Authorization': f'Token {API_TOKEN}',
    'Content-Type': 'application/json'
}

ALLOWED_STATUSES = ['Not Started', 'In Progress', 'On Hold']

@app.route('/')
def index():
    return render_template('engagement.html')

@app.route('/api/engagements')
def get_engagements():
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)

        # Get filter parameters
        task_name = request.args.get('task_name', '').lower()
        status_filter = request.args.get('status', '')
        assigned_to = request.args.get('assigned_to', '')
        mentor_status = request.args.get('mentor_status', '')
        lead_status = request.args.get('lead_status', '')
        product_filter = request.args.get('product', '')
        created_from = request.args.get('created_from', '')
        created_to = request.args.get('created_to', '')
        appsec_from = request.args.get('appsec_eta_from', '')
        appsec_to = request.args.get('appsec_eta_to', '')
        rm_from = request.args.get('rm_eta_from', '')
        rm_to = request.args.get('rm_eta_to', '')

        api_url = f'{API_BASE_URL}/api/v2/engagements/?limit=1000'
        response = requests.get(api_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()

        users_map = get_users_map()
        products_map = get_products_map()

        all_engagements = []
        for eng in data.get('results', []) or []:
            if not eng or eng.get('status') not in ALLOWED_STATUSES:
                continue

            # Calculate aging
            created = eng.get('created', '')
            aging = 0
            if created:
                try:
                    created_date = datetime.strptime(created[:10], '%Y-%m-%d')
                    aging = (datetime.now() - created_date).days
                except:
                    pass

            lead_id = eng.get('lead')
            lead_name = users_map.get(lead_id, 'N/A') if lead_id else 'N/A'

            product_id = eng.get('product')
            product_name = products_map.get(product_id, 'N/A') if product_id else 'N/A'

            updated = eng.get('updated', '')
            if updated:
                try:
                    updated_dt = datetime.strptime(updated[:19], '%Y-%m-%dT%H:%M:%S')
                    updated = updated_dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    updated = updated[:10] if len(updated) >= 10 else updated

            engagement = {
                'id': eng.get('id'),
                'created': created[:10] if created else 'N/A',
                'aging': aging,
                'name': eng.get('name', 'N/A'),
                'lead': lead_name,
                'lead_id': lead_id,
                'target_start': eng.get('target_start') or 'N/A',
                'target_end': eng.get('target_end') or 'N/A',
                'status': eng.get('status', 'N/A'),
                'build_id': eng.get('build_id') or 'N/A',
                'commit_hash': eng.get('commit_hash') or 'N/A',
                'product': product_name,
                'product_id': product_id,
                'version': eng.get('version') or 'N/A',
                'updated': updated,
                'description': eng.get('description', '')
            }

            # Apply filters
            if task_name and task_name not in engagement['name'].lower():
                continue
            if status_filter and status_filter != engagement['status']:
                continue
            if assigned_to and str(assigned_to) != str(lead_id):
                continue
            if mentor_status and mentor_status != engagement['build_id']:
                continue
            if lead_status and lead_status != engagement['commit_hash']:
                continue
            if product_filter and str(product_filter) != str(product_id):
                continue
            if created_from and engagement['created'] != 'N/A':
                if engagement['created'] < created_from:
                    continue
            if created_to and engagement['created'] != 'N/A':
                if engagement['created'] > created_to:
                    continue
            if appsec_from and engagement['target_start'] != 'N/A':
                if engagement['target_start'] < appsec_from:
                    continue
            if appsec_to and engagement['target_start'] != 'N/A':
                if engagement['target_start'] > appsec_to:
                    continue
            if rm_from and engagement['target_end'] != 'N/A':
                if engagement['target_end'] < rm_from:
                    continue
            if rm_to and engagement['target_end'] != 'N/A':
                if engagement['target_end'] > rm_to:
                    continue

            all_engagements.append(engagement)

        total = len(all_engagements)
        start = (page - 1) * limit
        end = start + limit

        return jsonify({
            'success': True,
            'data': all_engagements[start:end],
            'total': total,
            'page': page,
            'limit': limit
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tests')
def get_tests():
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)

        # Get filter parameters
        title_filter = request.args.get('title', '').strip().lower()
        jira_status_filter = request.args.get('jira_status', '').strip()
        jira_type_filter = request.args.get('jira_type', '').strip()
        analysis_status_filter = request.args.get('analysis_status', '').strip()
        assigned_to_filter = request.args.get('assigned_to', '').strip()
        build_type_filter = request.args.get('build_type', '').strip()
        task_filter = request.args.get('task', '').strip()

        api_url = f'{API_BASE_URL}/api/v2/tests/?limit=1000'
        response = requests.get(api_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()

        users_map = get_users_map()
        engagements_map = get_engagements_map()
        environments_map = get_environments_map()

        filtered_tests = []
        for test in data.get('results', []) or []:
            if not test:
                continue

            # Must have mcr_jira tag
            tags = test.get('tags', []) or []
            has_mcr_jira = any(tag for tag in tags if tag and 'mcr_jira' in str(tag).lower())

            if not has_mcr_jira:
                continue

            # NEW: Must have build_id = Pending or On Hold
            build_id = test.get('build_id', '').strip()
            if build_id not in ['Pending', 'On Hold']:
                continue

            created = test.get('created', '')
            if created:
                try:
                    created = datetime.strptime(created[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
                except:
                    created = created[:10] if len(created) >= 10 else created

            title = test.get('title', '')
            branch_tag = test.get('branch_tag', '')
            commit_hash = test.get('commit_hash', '')
            lead_id = test.get('lead')
            environment_id = test.get('environment')
            engagement_id = test.get('engagement')

            # Apply filters
            if title_filter and title_filter not in title.lower():
                continue

            if jira_status_filter and jira_status_filter != branch_tag:
                continue

            if jira_type_filter and jira_type_filter != commit_hash:
                continue

            if analysis_status_filter and analysis_status_filter != build_id:
                continue

            if assigned_to_filter and str(assigned_to_filter) != str(lead_id):
                continue

            if build_type_filter and str(build_type_filter) != str(environment_id):
                continue

            if task_filter and str(task_filter) != str(engagement_id):
                continue

            test_obj = {
                'id': test.get('id'),
                'created': created,
                'title': title,
                'branch_tag': branch_tag,
                'commit_hash': commit_hash,
                'build_id': build_id,
                'lead': users_map.get(lead_id, 'N/A'),
                'lead_id': lead_id,
                'environment': environments_map.get(environment_id, 'N/A'),
                'environment_id': environment_id,
                'engagement': engagements_map.get(engagement_id, 'N/A'),
                'engagement_id': engagement_id,
                'target_start': test.get('target_start', ''),
                'target_end': test.get('target_end', ''),
                'test_type': test.get('test_type'),
                'test_type_name': test.get('test_type_name', '')
            }

            filtered_tests.append(test_obj)

        total = len(filtered_tests)
        start = (page - 1) * limit
        end = start + limit

        return jsonify({
            'success': True,
            'data': filtered_tests[start:end],
            'total': total,
            'page': page,
            'limit': limit
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-filter-options')
def get_test_filter_options():
    try:
        api_url = f'{API_BASE_URL}/api/v2/tests/?limit=1000'
        response = requests.get(api_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()

        users_map = get_users_map()
        engagements_map = get_engagements_map()
        environments_map = get_environments_map()

        jira_status_set = set()
        jira_type_set = set()
        analysis_status_set = set()
        assigned_to_dict = {}
        build_type_dict = {}
        task_dict = {}

        for test in data.get('results', []) or []:
            if not test:
                continue

            tags = test.get('tags', []) or []
            has_mcr_jira = any(tag for tag in tags if tag and 'mcr_jira' in str(tag).lower())

            if not has_mcr_jira:
                continue

            # Only include Pending/On Hold tests
            build_id = test.get('build_id', '').strip()
            if build_id not in ['Pending', 'On Hold']:
                continue

            # Collect Jira Status (branch_tag)
            branch_tag = test.get('branch_tag', '').strip()
            if branch_tag:
                jira_status_set.add(branch_tag)

            # Collect Jira Type (commit_hash)
            commit_hash = test.get('commit_hash', '').strip()
            if commit_hash:
                jira_type_set.add(commit_hash)

            # Collect Analysis Status (build_id)
            if build_id:
                analysis_status_set.add(build_id)

            # Collect Assigned To (lead)
            lead_id = test.get('lead')
            if lead_id and lead_id in users_map:
                assigned_to_dict[lead_id] = users_map[lead_id]

            # Collect Build Type (environment)
            env_id = test.get('environment')
            if env_id and env_id in environments_map:
                build_type_dict[env_id] = environments_map[env_id]

            # Collect Task (engagement)
            eng_id = test.get('engagement')
            if eng_id and eng_id in engagements_map:
                task_dict[eng_id] = engagements_map[eng_id]

        return jsonify({
            'success': True,
            'jira_status': sorted(list(jira_status_set)),
            'jira_type': sorted(list(jira_type_set)),
            'analysis_status': sorted(list(analysis_status_set)),
            'assigned_to': sorted([{'id': k, 'name': v} for k, v in assigned_to_dict.items()], key=lambda x: x['name']),
            'build_type': sorted([{'id': k, 'name': v} for k, v in build_type_dict.items()], key=lambda x: x['name']),
            'task': sorted([{'id': k, 'name': v} for k, v in task_dict.items()], key=lambda x: x['name'])
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/filter-options')
def get_filter_options():
    try:
        api_url = f'{API_BASE_URL}/api/v2/engagements/?limit=1000'
        response = requests.get(api_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()

        users_map = get_users_map()
        products_map = get_products_map()

        results = data.get('results', []) or []
        assigned_to_set = set()
        mentor_status_set = set()
        lead_status_set = set()
        product_set = set()

        for eng in results:
            if not eng or eng.get('status') not in ALLOWED_STATUSES:
                continue

            lead_id = eng.get('lead')
            if lead_id and lead_id in users_map:
                lead_name = users_map[lead_id]
                if lead_name and lead_name != 'N/A':
                    assigned_to_set.add((lead_id, lead_name))

            # NEW: Populate Mentor Status from build_id column
            build_id = eng.get('build_id')
            if build_id and build_id != 'N/A':
                mentor_status_set.add(build_id)

            # NEW: Populate Lead Status from commit_hash column
            commit_hash = eng.get('commit_hash')
            if commit_hash and commit_hash != 'N/A':
                lead_status_set.add(commit_hash)

            product_id = eng.get('product')
            if product_id and product_id in products_map:
                product_name = products_map[product_id]
                if product_name and product_name != 'N/A':
                    product_set.add((product_id, product_name))

        return jsonify({
            'success': True,
            'assigned_to': sorted([{'id': aid, 'name': name} for aid, name in assigned_to_set], key=lambda x: x['name']),
            'mentor_status': sorted(list(mentor_status_set)),
            'lead_status': sorted(list(lead_status_set)),
            'products': sorted([{'id': pid, 'name': name} for pid, name in product_set], key=lambda x: x['name'])
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/engagement/<int:engagement_id>', methods=['PUT'])
def update_engagement(engagement_id):
    try:
        data = request.get_json()
        payload = {
            'name': data.get('name'),
            'target_start': data.get('target_start'),
            'target_end': data.get('target_end'),
            'lead': int(data.get('lead')),
            'product': int(data.get('product'))
        }

        if data.get('status'):
            payload['status'] = data.get('status')
        if data.get('build_id'):
            payload['build_id'] = data.get('build_id')
        if data.get('commit_hash'):
            payload['commit_hash'] = data.get('commit_hash')
        if data.get('version'):
            payload['version'] = data.get('version')
        if 'description' in data:
            payload['description'] = data.get('description')

        api_url = f'{API_BASE_URL}/api/v2/engagements/{engagement_id}/'
        response = requests.put(api_url, headers=HEADERS, json=payload, timeout=30)
        response.raise_for_status()

        return jsonify({'success': True, 'message': 'Updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test/<int:test_id>', methods=['PUT'])
def update_test(test_id):
    try:
        data = request.get_json()
        payload = {
            'title': data.get('title'),
            'target_start': data.get('target_start'),
            'target_end': data.get('target_end'),
            'test_type_name': data.get('test_type_name'),
            'engagement': int(data.get('engagement')),
            'lead': int(data.get('lead')),
            'test_type': int(data.get('test_type')),
            'environment': int(data.get('environment'))
        }

        if data.get('build_id'):
            payload['build_id'] = data.get('build_id')

        api_url = f'{API_BASE_URL}/api/v2/tests/{test_id}/'
        response = requests.put(api_url, headers=HEADERS, json=payload, timeout=30)
        response.raise_for_status()

        return jsonify({'success': True, 'message': 'Updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/jira-counts', methods=['POST'])
def get_jira_counts():
    try:
        data = request.get_json()
        engagement_ids = data.get('engagement_ids', [])

        results = {}
        for eng_id in engagement_ids:
            api_url = f'{API_BASE_URL}/api/v2/tests/?engagement={eng_id}&limit=1000'
            response = requests.get(api_url, headers=HEADERS, timeout=30)
            tests = response.json().get('results', []) or []

            counts = {'T': 0, 'C': 0, 'P': 0, 'S': 0, 'F': 0, 'D': 0, 'ND': 0}

            for test in tests:
                if not test:
                    continue
                tags = test.get('tags', []) or []
                if not any(tag for tag in tags if tag and 'mcr_jira' in str(tag).lower()):
                    continue

                counts['T'] += 1

                build_id = str(test.get('build_id', '')).strip().lower()
                commit_hash = str(test.get('commit_hash', '')).strip().lower()
                branch = str(test.get('branch_tag', '')).strip().lower()

                if build_id in ['approved', 'rejected']:
                    counts['C'] += 1
                if build_id in ['pending', 'on hold']:
                    counts['P'] += 1
                if commit_hash == 'security':
                    counts['S'] += 1
                if commit_hash and commit_hash != 'security':
                    counts['F'] += 1
                if branch in ['ready for testing', 'ready for security', 'done']:
                    counts['D'] += 1
                if branch and branch not in ['ready for testing', 'ready for security', 'done']:
                    counts['ND'] += 1

            results[str(eng_id)] = counts

        return jsonify({'success': True, 'counts': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/summary/engagements')
def get_engagement_summary():
    try:
        api_url = f'{API_BASE_URL}/api/v2/engagements/?limit=1000'
        response = requests.get(api_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()

        users_map = get_users_map()

        # NEW: Count by lead and status (3 columns)
        lead_status_counts = {}

        for eng in data.get('results', []) or []:
            if not eng or eng.get('status') not in ALLOWED_STATUSES:
                continue

            lead_id = eng.get('lead')
            if not lead_id:
                continue

            lead_name = users_map.get(lead_id, 'Unknown')
            status = eng.get('status')

            if lead_name not in lead_status_counts:
                lead_status_counts[lead_name] = {
                    'Not Started': 0,
                    'In Progress': 0,
                    'On Hold': 0
                }

            lead_status_counts[lead_name][status] += 1

        # Format for display
        summary = []
        for lead_name in sorted(lead_status_counts.keys()):
            row = {
                'lead': lead_name,
                'not_started': lead_status_counts[lead_name]['Not Started'],
                'in_progress': lead_status_counts[lead_name]['In Progress'],
                'on_hold': lead_status_counts[lead_name]['On Hold'],
                'total': sum(lead_status_counts[lead_name].values())
            }
            summary.append(row)

        # Calculate column totals
        col_totals = {
            'not_started': sum(row['not_started'] for row in summary),
            'in_progress': sum(row['in_progress'] for row in summary),
            'on_hold': sum(row['on_hold'] for row in summary),
            'total': sum(row['total'] for row in summary)
        }

        return jsonify({
            'success': True,
            'data': summary,
            'col_totals': col_totals
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/summary/jiras')
def get_jira_summary():
    try:
        tests_url = f'{API_BASE_URL}/api/v2/tests/?limit=1000'
        tests_response = requests.get(tests_url, headers=HEADERS, timeout=30)
        tests_response.raise_for_status()
        tests_data = tests_response.json()

        users_map = get_users_map()
        environments_map = get_environments_map()

        # NEW: Count by lead, environment, AND build_id (Pending/On Hold sub-columns)
        env_ids = set()
        lead_env_build_counts = {}

        for test in tests_data.get('results', []) or []:
            if not test:
                continue

            tags = test.get('tags', []) or []
            has_mcr_jira = any(tag for tag in tags if tag and 'mcr_jira' in str(tag).lower())
            if not has_mcr_jira:
                continue

            build_id = test.get('build_id', '').strip()
            if build_id not in ['Pending', 'On Hold']:
                continue

            lead_id = test.get('lead')
            env_id = test.get('environment')

            if not lead_id or not env_id:
                continue

            env_ids.add(env_id)
            lead_name = users_map.get(lead_id, 'Unknown')

            if lead_name not in lead_env_build_counts:
                lead_env_build_counts[lead_name] = {}

            if env_id not in lead_env_build_counts[lead_name]:
                lead_env_build_counts[lead_name][env_id] = {'Pending': 0, 'On Hold': 0}

            lead_env_build_counts[lead_name][env_id][build_id] += 1

        env_list = sorted([{'id': eid, 'name': environments_map.get(eid, 'Unknown')} 
                          for eid in env_ids], key=lambda x: x['name'])

        # Format data
        summary = []
        for lead_name in sorted(lead_env_build_counts.keys()):
            row = {'lead': lead_name}
            row_total = 0

            for env in env_list:
                pending = lead_env_build_counts[lead_name].get(env['id'], {}).get('Pending', 0)
                on_hold = lead_env_build_counts[lead_name].get(env['id'], {}).get('On Hold', 0)

                row[f"env_{env['id']}_pending"] = pending
                row[f"env_{env['id']}_onhold"] = on_hold
                row_total += pending + on_hold

            row['total'] = row_total
            summary.append(row)

        # Calculate column totals
        col_totals = {}
        grand_total = 0

        for env in env_list:
            pending_total = sum(row.get(f"env_{env['id']}_pending", 0) for row in summary)
            onhold_total = sum(row.get(f"env_{env['id']}_onhold", 0) for row in summary)

            col_totals[f"env_{env['id']}_pending"] = pending_total
            col_totals[f"env_{env['id']}_onhold"] = onhold_total
            grand_total += pending_total + onhold_total

        return jsonify({
            'success': True,
            'data': summary,
            'environments': env_list,
            'col_totals': col_totals,
            'grand_total': grand_total
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def get_users_map():
    try:
        response = requests.get(f'{API_BASE_URL}/api/v2/users/?limit=1000', headers=HEADERS, timeout=30)
        users = response.json().get('results', []) or []

        users_map = {}
        for user in users:
            if not user:
                continue
            user_id = user.get('id')
            first_name = user.get('first_name', '') or ''
            last_name = user.get('last_name', '') or ''
            full_name = f"{first_name} {last_name}".strip() or user.get('username', 'N/A')
            users_map[user_id] = full_name

        return users_map
    except:
        return {}

def get_products_map():
    try:
        response = requests.get(f'{API_BASE_URL}/api/v2/products/?limit=1000', headers=HEADERS, timeout=30)
        products = response.json().get('results', []) or []
        return {p.get('id'): p.get('name', 'N/A') for p in products if p}
    except:
        return {}

def get_engagements_map():
    try:
        response = requests.get(f'{API_BASE_URL}/api/v2/engagements/?limit=1000', headers=HEADERS, timeout=30)
        engagements = response.json().get('results', []) or []
        return {e.get('id'): e.get('name', 'N/A') for e in engagements if e}
    except:
        return {}

def get_environments_map():
    try:
        response = requests.get(f'{API_BASE_URL}/api/v2/development_environments/?limit=1000', headers=HEADERS, timeout=30)
        environments = response.json().get('results', []) or []
        return {e.get('id'): e.get('name', 'N/A') for e in environments if e}
    except:
        return {}

if __name__ == '__main__':
    print("=" * 60)
    print("Starting DefectDojo Engagement Manager v1.0.11")
    print("=" * 60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Server: http://127.0.0.1:5000")
    print("=" * 60)
    print("Press CTRL+C to stop")
    print("=" * 60)
    app.run(debug=True, host='127.0.0.1', port=5000)
