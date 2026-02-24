INSERT INTO public.users (id, email, iap_id, role, approver_threshold)
VALUES ('019c8f72-9f92-7f22-8faa-000000000001', 'admin@t.ru', 'admin', 'ADMIN', 0),
       ('019c8f72-9f92-7f22-8faa-000000000002', 'exp@t.ru', 'exp', 'EXPERIMENTER', 1),
       ('019c8f72-9f92-7f22-8faa-000000000003', 'approver@t.ru', 'approver', 'APPROVER', 0),
       ('019c8f72-9f92-7f22-8faa-000000000005', 'approver2@t.ru', 'approver2', 'APPROVER', 0),
       ('019c8f72-9f92-7f22-8faa-000000000004', 'viewer@t.ru', 'viewer', 'VIEWER', 0);

INSERT INTO public.assigned_approvers (experimenter_id, approver_id)
VALUES ('019c8f72-9f92-7f22-8faa-000000000002', '019c8f72-9f92-7f22-8faa-000000000003');

INSERT INTO public.event_types (id, name, schema, requires_attribution, is_archived)
VALUES ('exposure', 'Exposure', '{
  "type": "object"
}', NULL, false),
       ('click', 'Button Click', '{
         "type": "object"
       }', 'exposure', false),
       ('error', 'App Error', '{
         "type": "object"
       }', NULL, false),
       ('check_types', 'Type check test', '{
         "type": "object",
         "properties": {
           "number": {
             "type": "number"
           }
         },
         "required": [
           "number"
         ]
       }', NULL, false),
       ('check_required', 'Required field check test', '{
         "type": "object",
         "properties": {
           "number": {
             "type": "number"
           }
         },
         "required": [
           "number"
         ]
       }', NULL, false),
       ('cannot_attribute', 'Cannot be attributed', '{
         "type": "object"
       }', 'non_existent_event', false);

INSERT INTO public.metrics (key, expression, compiled)
VALUES ('ctr',
        'count attributed click / count exposure',
        '[
          {
            "table": "events",
            "where": "event_type = ''click'' AND status = ''accepted''",
            "select": "count()"
          },
          {
            "table": "events",
            "where": "event_type = ''exposure''",
            "select": "count()"
          }
        ]'::jsonb),
       ('errors',
        'count error',
        '[
          {
            "table": "events",
            "where": "event_type = ''error''",
            "select": "count()"
          },
          null
        ]'::jsonb),
       ('clicks',
        'count attributed *',
        '[
          {
            "table": "events",
            "where": "event_type = ''click'' AND status = ''accepted''",
            "select": "count()"
          },
          null
        ]'::jsonb),
       ('all_events',
        'count *',
        '[
          {
            "table": "events",
            "where": "1=1",
            "select": "count()"
          },
          null
        ]'::jsonb);

INSERT INTO public.flags (key, description, type, "default", author_id, created_at, updated_at)
VALUES ('flag_simple', 'Simple Feature', 'STRING', 'off', '019c8f72-9f92-7f22-8faa-000000000002', NOW(), NOW()),
       ('flag_no_exp', 'No experiment', 'STRING', 'default', '019c8f72-9f92-7f22-8faa-000000000002', NOW(), NOW()),
       ('flag_targeted', 'Targeted Feature', 'STRING', 'default', '019c8f72-9f92-7f22-8faa-000000000002', NOW(), NOW()),
       ('flag_active', 'Main Button Color', 'STRING', 'blue', '019c8f72-9f92-7f22-8faa-000000000002', NOW(), NOW()),
       ('flag_guard', 'Risky Algorithm', 'STRING', 'legacy', '019c8f72-9f92-7f22-8faa-000000000002', NOW(), NOW()),
       ('flag_conflict', 'Checkout Layout', 'STRING', 'v1', '019c8f72-9f92-7f22-8faa-000000000002', NOW(), NOW());

INSERT INTO public.experiments_latest (id, name, flag_key, state, version, audience,
                                       variants, targeting, author_id, created_at, updated_at,
                                       priority, conflict_domain, conflict_policy, metrics)
VALUES ('019c8f72-9f92-7f22-8faa-0000000000e0', 'Button Color Test', 'flag_active', 'STARTED', 1, 100,
        '[
          {
            "name": "control",
            "value": "blue",
            "audience": 50,
            "is_control": true
          },
          {
            "name": "treatment",
            "value": "red",
            "audience": 50,
            "is_control": false
          }
        ]'::jsonb,
        NULL,
        '019c8f72-9f92-7f22-8faa-000000000002', NOW(), NOW(),
        1, 'default', 'ONE_OR_NONE',
        '{
          "primary": "ctr",
          "secondary": ["all_events", "clicks"],
          "guarding": []
        }');

INSERT INTO public.experiments_latest (id, name, flag_key, state, version, audience, variants, targeting, author_id,
                                       created_at, updated_at, metrics)
VALUES ('019c8f72-9f92-7f22-8faa-0000000000e1', 'RU Only Test', 'flag_targeted', 'STARTED', 1, 100,
        '[
          {
            "name": "control",
            "value": "ru_default",
            "audience": 50,
            "is_control": true
          },
          {
            "name": "ru_variant",
            "value": "ru_special",
            "audience": 50,
            "is_control": false
          }
        ]'::jsonb,
        'country == "RU"',
        '019c8f72-9f92-7f22-8faa-000000000002', NOW(), NOW(),
        '{
          "primary": "ctr",
          "secondary": [],
          "guarding": []
        }'::jsonb);

INSERT INTO public.experiments_latest (id, name, flag_key, state, version, audience, variants, author_id, created_at,
                                       updated_at, metrics)
VALUES ('019c8f72-9f92-7f22-8faa-0000000000e2', 'Future Test', 'flag_simple', 'DRAFT', 1, 10,
        '[
          {
            "name": "A",
            "value": "on",
            "audience": 100,
            "is_control": false
          }
        ]'::jsonb,
        '019c8f72-9f92-7f22-8faa-000000000002', NOW(), NOW(),
        '{
          "primary": "ctr",
          "secondary": [],
          "guarding": []
        }'::jsonb),
       ('019c8f72-9f92-7f22-8faa-0000000000e3', 'Waiting Approval', 'flag_simple', 'IN_REVIEW', 1, 10,
        '[
          {
            "name": "A",
            "value": "on",
            "audience": 100,
            "is_control": false
          }
        ]'::jsonb,
        '019c8f72-9f92-7f22-8faa-000000000002', NOW(), NOW(),
        '{
          "primary": "ctr",
          "secondary": [],
          "guarding": []
        }'::jsonb);

INSERT INTO public.experiments_latest (id, name, flag_key, state, version, audience, variants, author_id, created_at,
                                       updated_at, metrics)
VALUES ('019c8f72-9f92-7f22-8faa-0000000000e4', 'Risky Rollout', 'flag_guard', 'STARTED', 1, 100,
        '[
          {
            "name": "safe",
            "value": "legacy",
            "audience": 10,
            "is_control": true
          },
          {
            "name": "risky",
            "value": "canary",
            "audience": 90,
            "is_control": false
          }
        ]'::jsonb,
        '019c8f72-9f92-7f22-8faa-000000000002', NOW(), NOW(),
        '{
          "primary": "ctr",
          "secondary": [],
          "guarding": ["errors"]
        }'::jsonb);

INSERT INTO public.experiments_latest (id, name, flag_key, state, version, audience, variants, author_id, created_at,
                                       updated_at,
                                       priority, conflict_domain, conflict_policy, metrics)
VALUES ('019c8f72-9f92-7f22-8faa-0000000000e5', 'Low Prio Text', 'flag_conflict', 'STARTED', 1, 100,
        '[
          {
            "name": "B",
            "value": "text_change",
            "audience": 100,
            "is_control": false
          }
        ]'::jsonb,
        '019c8f72-9f92-7f22-8faa-000000000002', NOW(), NOW(),
        10, 'checkout_page', 'HIGHER_PRIORITY',
        '{
          "primary": "ctr",
          "secondary": [],
          "guarding": []
        }'::jsonb);

INSERT INTO public.experiments_latest (id, name, flag_key, state, version, audience, variants, author_id, created_at,
                                       updated_at,
                                       priority, conflict_domain, conflict_policy, metrics)
VALUES ('019c8f72-9f92-7f22-8faa-0000000000e6', 'High Prio Button', 'flag_conflict', 'STARTED', 1, 100,
        '[
          {
            "name": "C",
            "value": "color_change",
            "audience": 100,
            "is_control": false
          }
        ]'::jsonb,
        '019c8f72-9f92-7f22-8faa-000000000002', NOW(), NOW(),
        100, 'checkout_page', 'HIGHER_PRIORITY',
        '{
          "primary": "ctr",
          "secondary": [],
          "guarding": []
        }'::jsonb);

INSERT INTO public.guard_rules (id, experiment_id, metric_key, threshold, watch_window_s, action, is_archived)
VALUES ('gr_error_check', '019c8f72-9f92-7f22-8faa-0000000000e4', 'errors', 1.0, 3209600, 'PAUSE', false);

INSERT INTO public.notification_rules (id, trigger_type, trigger_resource, connection_string, message_template,
                                       rate_limit_s)
VALUES ('notif_console', 'guardrail', 'gr_error_check', 'email://test@t.ru',
        'ALERT: Experiment {{experiment_id}} triggered guardrail for metric {{metric_key}} ({{metric_value}})!', 60);

INSERT INTO public.experiments_latest (id, name, flag_key, state, version, audience, variants, author_id, created_at,
                                       updated_at, result_outcome, result_comment, metrics)
VALUES ('019c8f72-9f92-7f22-8faa-0000000000e7', 'Old Report', 'flag_simple', 'FINISHED', 2, 100,
        '[
          {
            "name": "control",
            "value": "off",
            "audience": 50,
            "is_control": true
          },
          {
            "name": "on",
            "value": "on",
            "audience": 50,
            "is_control": false
          }
        ]'::jsonb,
        '019c8f72-9f92-7f22-8faa-000000000002', NOW() - INTERVAL '7 days', NOW(),
        'ROLLOUT_WINNER', 'This turned out to be super good!',
        '{
          "primary": "ctr",
          "secondary": [],
          "guarding": []
        }'::jsonb);

INSERT INTO public.reports (id, experiment_id, start_at, end_at)
VALUES ('019c8fed-7b54-7c86-80cc-f0769fa0a16c',
        '019c8f72-9f92-7f22-8faa-0000000000e0',
        '2026-02-20 13:53:37.713000',
        '2026-03-18 13:53:37.713000'),
    ('019c8fed-7b54-7c86-80cc-f0769fa0a16d',
        '019c8f72-9f92-7f22-8faa-0000000000e4',
        '2026-02-20 13:53:37.713000',
        '2026-03-18 13:53:37.713000');
