# MySQL 5.7 to 8.0 Upgrade Assessment for database-3
Generated: 2025-12-12 23:08:57

## Overview
- Total Databases: 1
- Databases Needing Upgrade: 1
- Total Issues: 222
- Blocking Issues: 38
- Warnings: 0

## Overall Status: RED

## Immediate Actions Required
- <strong>Deprecated Features Check</strong> (12 issues): Update authentication to caching_sha2_password for all users
- <strong>Parameter Compatibility Check</strong> (15 issues): Remove or replace parameters that will be removed in 8.0
- <strong>Reserved Keywords Conflicts</strong> (7 issues): CRITICAL: Rename objects that conflict with reserved keywords before upgrading
- <strong>Spatial Data SRID Requirements</strong> (2 issues): CRITICAL: All spatial columns require explicit SRID in MySQL 8.0:
- <strong>Auto-Increment Exhaustion</strong> (2 issues): CRITICAL: Auto-increment exhaustion detected!

## Upgrade Order
- Aurora cluster database-3 (5.7.mysql_aurora.2.12.3)

## Common Issues Found
-   View: customer_orders
    Updatable: NO
    Security: DEFINER
    Definer: admin@%
    Character Set: utf8mb4
    Potential Issues: May need ANY_VALUE() for GROUP BY in 8.0

-   Table: customer_preferences
    Column: preference_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: heavily_partitioned
    Column: data
    Type: varchar(100)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: customer_addresses
    Column: address_type
    Type: enum('billing','shipping','both')
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
-   Table: sales_history
    Column: amount
    Type: decimal(10,2)
    Current Charset: None
    Current Collation: None
-   Table: session_data
    Column: user_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   FK: fk_orderitems_orders
    Table: order_items.order_id
    References: upgrade_test_good.orders.order_id
    Update Rule: CASCADE, Delete Rule: RESTRICT
    Supporting Index: idx_order
-   Table: parent_table
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
- Deprecated system variable in use: tx_read_only
-   Table: customer_data
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: product_images
    Column: image_url
    Type: varchar(500)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
- CRITICAL: Table 'upgrade_test.orders_tinyint' auto-increment at 94.1% capacity (240 of 255)
-   Table: customer_preferences
    Column: preferences
    Type: json
    Current Charset: None
    Current Collation: None
- Server character set: latin1
-   Table: window
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: sales_transactions
    Column: payment_method
    Type: varchar(50)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
- Parameter will be removed in 8.0: innodb_file_format_max
-   FK: fk_orderitems_products
    Table: order_items.product_id
    References: upgrade_test_good.products.product_id
    Update Rule: CASCADE, Delete Rule: RESTRICT
    Supporting Index: idx_product
-   Table: customers
    Column: email
    Type: varchar(255)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_unicode_ci
-   Trigger: trg_order_audit_update
    On Table: orders
    Event: AFTER UPDATE
    Created: 2025-12-12 23:11:07.140000
    Definer: admin@%
    Character Set: utf8mb4

-   Table: product_reviews
    Column: product_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: child_table
    Column: info
    Type: varchar(100)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: sales_data
    Column: over
    Type: varchar(50)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: product_categories
    Column: category_name
    Type: varchar(100)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
- Deprecated system variable in use: multi_range_count
-   Table: audit_log
    Column: old_value
    Type: text
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
- Table name 'upgrade_test.system' conflicts with MySQL 8.0 reserved keyword
-   Table: large_data_table
    Column: data4
    Type: varchar(255)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: latin1_table
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: event_logs
    Column: log_id
    Type: bigint(20) unsigned
    Current Charset: None
    Current Collation: None
-   Table: large_data_table
    Column: data1
    Type: varchar(255)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: system
    Column: name
    Type: varchar(50)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: heavily_partitioned
    Column: created_date
    Type: date
    Current Charset: None
    Current Collation: None
-   Table: products
    Column: product_name
    Type: varchar(200)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_unicode_ci
-   Table: orders
    Column: order_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
- Found 6 JSON columns (6 without indexes)
-   Table: locations
    Column: area
    Type: polygon
    Current Charset: None
    Current Collation: None
-   Table: order_items
    Column: item_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: sales_transactions
    Column: transaction_date
    Type: datetime
    Current Charset: None
    Current Collation: None
-   Table: child_table
    Column: parent_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: locations
    Column: name
    Type: varchar(100)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: customer_data
    Column: email
    Type: varchar(255)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: audit_log
    Column: action
    Type: varchar(10)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: order_items
    Column: quantity
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: product_categories
    Column: parent_category_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: session_data
    Column: session_id
    Type: int(10) unsigned
    Current Charset: None
    Current Collation: None
-   Table: sales_transactions
    Column: transaction_status
    Type: varchar(20)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
-   Table: session_data
    Column: session_token
    Type: varchar(255)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Trigger: before_parent_update
    On Table: parent_table
    Event: BEFORE UPDATE
    Created: 2025-12-12 23:12:28.510000
    Definer: admin@%
    Character Set: utf8mb4

-   Table: sales_data
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: products
    Column: stock_quantity
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: product_reviews
    Column: review_date
    Type: datetime
    Current Charset: None
    Current Collation: None
- Column name 'upgrade_test.sales_data.over' conflicts with MySQL 8.0 reserved keyword
-   Table: sales_history
    Column: customer_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
- 
Triggers:
-   Table: user_passwords
    Column: username
    Type: varchar(50)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
- Parameter innodb_autoinc_lock_mode default changing to 2
-   Table: orders_tinyint
    Column: item_code
    Type: varchar(20)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: sales_data
    Column: lag
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: user_passwords
    Column: password_hash
    Type: varchar(100)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: product_images
    Column: image_alt_text
    Type: varchar(200)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
-   Table: customer_addresses
    Column: customer_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: orders
    Column: total_amount
    Type: decimal(10,2)
    Current Charset: None
    Current Collation: None
-   Table: customer_addresses
    Column: city
    Type: varchar(100)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
-   Table: child_table
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: sales_data
    Column: lead
    Type: decimal(10,2)
    Current Charset: None
    Current Collation: None
-   Table: audit_trail
    Column: table_name
    Type: varchar(50)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
- Column name 'upgrade_test.sales_data.lead' conflicts with MySQL 8.0 reserved keyword
- Parameter will be removed in 8.0: max_tmp_tables
-   Table: audit_log
    Column: new_value
    Type: text
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: customer_preferences
    Column: customer_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
- Parameter will be removed in 8.0: innodb_support_xa
-   Table: product_categories
    Column: display_order
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: customer_addresses
    Column: state_province
    Type: varchar(100)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
- Duplicate indexes on upgrade_test_good.user_accounts: 'idx_username' and 'username' (both on username)
-   Table: shipping_carriers
    Column: carrier_code
    Type: varchar(20)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
-   View: user_auth
    Updatable: YES
    Security: DEFINER
    Definer: admin@%
    Character Set: utf8mb4
    Potential Issues: Uses deprecated PASSWORD() function

- Parameter will be removed in 8.0: query_cache_type
-   Table: products
    Column: name
    Type: varchar(100)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
- Parameter will be removed in 8.0: innodb_large_prefix
-   Table: orders_smallint
    Column: customer_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: system
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Trigger: trg_order_audit_insert
    On Table: orders
    Event: AFTER INSERT
    Created: 2025-12-12 23:11:07.060000
    Definer: admin@%
    Character Set: utf8mb4

-   Table: inventory
    Column: warehouse_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
- CRITICAL: Table 'upgrade_test.orders_smallint' auto-increment at 91.6% capacity (60,000 of 65,535)
-   Table: sales_transactions
    Column: payment_amount
    Type: decimal(10,2)
    Current Charset: None
    Current Collation: None
-   Table: order_items
    Column: unit_price
    Type: decimal(10,2)
    Current Charset: None
    Current Collation: None
-   Table: shipping_carriers
    Column: is_active
    Type: tinyint(1)
    Current Charset: None
    Current Collation: None
-   Table: user_accounts
    Column: account_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
- Spatial column 'upgrade_test.locations.area' (polygon) requires explicit SRID for MySQL 8.0
-   Table: large_data_table
    Column: data5
    Type: text
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
- Parameter will be removed in 8.0: query_cache_size
-   Table: customer_addresses
    Column: country
    Type: varchar(100)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
- Found 4 users with deprecated authentication methods
- Critical parameter log_bin_trust_function_creators not set to required value 1
-   Table: large_data_table
    Column: created_at
    Type: timestamp
    Current Charset: None
    Current Collation: None
-   Table: customer_preferences
    Column: updated_at
    Type: timestamp
    Current Charset: None
    Current Collation: None
- Column name 'upgrade_test.sales_data.lag' conflicts with MySQL 8.0 reserved keyword
-   Table: user_accounts
    Column: user_email
    Type: varchar(255)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
- Parameter will be removed in 8.0: sync_frm
-   Table: sales_data
    Column: groups
    Type: varchar(100)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: event_logs
    Column: event_type
    Type: varchar(50)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: customers
    Column: last_name
    Type: varchar(100)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_unicode_ci
-   Table: sales_transactions
    Column: order_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: rank
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
- Duplicate indexes on upgrade_test.inventory: 'idx_product' and 'idx_product_dup' (both on product_code)
-   Table: latin1_table
    Column: name
    Type: varchar(100)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: product_reviews
    Column: review_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: shipping_carriers
    Column: tracking_url_template
    Type: varchar(500)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
-   Table: customers
    Column: created_at
    Type: timestamp
    Current Charset: None
    Current Collation: None
- Parameter will be removed in 8.0: secure_auth
-   Table: products
    Column: attributes
    Type: json
    Current Charset: None
    Current Collation: None
- 
Views:
- Spatial column 'upgrade_test.locations.coordinates' (point) requires explicit SRID for MySQL 8.0
- Table name 'upgrade_test.rank' conflicts with MySQL 8.0 reserved keyword
-   Table: old_utf8_table
    Column: description
    Type: text
    Current Charset: utf8
    Current Collation: utf8_general_ci
-   Table: sales_transactions
    Column: transaction_id
    Type: bigint(20)
    Current Charset: None
    Current Collation: None
- 
Schema: upgrade_test
-   Table: heavily_partitioned
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: customer_addresses
    Column: is_default
    Type: tinyint(1)
    Current Charset: None
    Current Collation: None
-   Table: shipping_carriers
    Column: carrier_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
- 
Schema: upgrade_test_good
-   Table: products
    Column: category
    Type: varchar(50)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_unicode_ci
- Query cache is enabled but will be removed in 8.0
-   Table: product_reviews
    Column: helpful_count
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: product_reviews
    Column: customer_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: parent_table
    Column: data
    Type: varchar(100)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: customer_data
    Column: created_at
    Type: datetime
    Current Charset: None
    Current Collation: None
-   Table: locations
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   FK: child_table_ibfk_1
    Table: child_table.parent_id
    References: upgrade_test.parent_table.id
    Update Rule: RESTRICT, Delete Rule: CASCADE
    Supporting Index: parent_id
-   Table: products
    Column: updated_at
    Type: timestamp
    Current Charset: None
    Current Collation: None
-   Table: customer_addresses
    Column: postal_code
    Type: varchar(20)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
-   Table: orders
    Column: order_date
    Type: date
    Current Charset: None
    Current Collation: None
-   Table: customer_addresses
    Column: street_address
    Type: varchar(255)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
- Deprecated system variable in use: innodb_file_format
-   Table: large_data_table
    Column: data2
    Type: text
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: orders
    Column: customer_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
- Parameter will be removed in 8.0: innodb_file_format
-   View: product_inventory
    Updatable: YES
    Security: DEFINER
    Definer: admin@%
    Character Set: utf8mb4

- Deprecated system variable in use: innodb_file_format_check
-   Table: product_images
    Column: is_primary
    Type: tinyint(1)
    Current Charset: None
    Current Collation: None
-   Table: audit_trail
    Column: action_type
    Type: varchar(20)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
-   Table: product_images
    Column: display_order
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: user_accounts
    Column: username
    Type: varchar(50)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
- Parameter will be removed in 8.0: multi_range_count
-   Table: inventory
    Column: quantity
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: session_data
    Column: user_agent
    Type: text
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: product_reviews
    Column: review_text
    Type: text
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
-   Table: locations
    Column: coordinates
    Type: point
    Current Charset: None
    Current Collation: None
-   Table: inventory
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: products
    Column: tags
    Type: json
    Current Charset: None
    Current Collation: None
- Deprecated system variable in use: secure_auth
-   Table: products
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: session_data
    Column: created_at
    Type: timestamp
    Current Charset: None
    Current Collation: None
- Found 2 spatial columns - review SRID requirements
-   Table: customer_data
    Column: full_name
    Type: varchar(200)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: audit_trail
    Column: record_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: session_data
    Column: ip_address
    Type: varchar(45)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: customer_data
    Column: metadata
    Type: json
    Current Charset: None
    Current Collation: None
-   Table: order_items
    Column: product_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
- Table name 'upgrade_test.window' conflicts with MySQL 8.0 reserved keyword
- Column name 'upgrade_test.sales_data.groups' conflicts with MySQL 8.0 reserved keyword
-   Table: product_reviews
    Column: rating
    Type: tinyint(4)
    Current Charset: None
    Current Collation: None
- Parameter will be removed in 8.0: innodb_file_format_check
- Deprecated system variable in use: innodb_file_format_max
-   Table: customers
    Column: first_name
    Type: varchar(100)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_unicode_ci
- Parameter will be removed in 8.0: log_warnings
-   Table: orders_smallint
    Column: order_id
    Type: smallint(5) unsigned
    Current Charset: None
    Current Collation: None
-   Table: audit_log
    Column: changed_at
    Type: timestamp
    Current Charset: None
    Current Collation: None
-   Table: audit_trail
    Column: changed_by
    Type: varchar(100)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
- Current version 5.7.44 needs upgrade to 8.0
-   Table: sales_history
    Column: sale_date
    Type: date
    Current Charset: None
    Current Collation: None
-   Table: shipping_carriers
    Column: carrier_name
    Type: varchar(100)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
-   Table: orders_tinyint
    Column: quantity
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: window
    Column: title
    Type: varchar(100)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: event_logs
    Column: created_at
    Type: timestamp
    Current Charset: None
    Current Collation: None
-   Table: customers
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: sales_history
    Column: sale_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: inventory
    Column: status
    Type: varchar(20)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
- Server collation: latin1_swedish_ci
-   Table: order_items
    Column: order_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: products
    Column: product_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
- Deprecated system variable in use: query_cache_size
-   FK: product_images_ibfk_1
    Table: product_images.product_id
    References: upgrade_test_good.products.product_id
    Update Rule: CASCADE, Delete Rule: CASCADE
    Supporting Index: idx_product
-   Table: audit_trail
    Column: audit_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: user_passwords
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: orders_smallint
    Column: order_date
    Type: date
    Current Charset: None
    Current Collation: None
-   Table: orders_smallint
    Column: total
    Type: decimal(10,2)
    Current Charset: None
    Current Collation: None
-   Table: event_logs
    Column: event_data
    Type: json
    Current Charset: None
    Current Collation: None
-   FK: customer_addresses_ibfk_1
    Table: customer_addresses.customer_id
    References: upgrade_test_good.customers.id
    Update Rule: CASCADE, Delete Rule: CASCADE
    Supporting Index: idx_customer
-   Table: old_utf8_table
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: user_accounts
    Column: registration_date
    Type: datetime
    Current Charset: None
    Current Collation: None
-   Table: large_data_table
    Column: data3
    Type: blob
    Current Charset: None
    Current Collation: None
-   Table: product_categories
    Column: category_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: audit_log
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
- Deprecated system variable in use: query_cache_type
- Deprecated system variable in use: tx_isolation
-   Table: large_data_table
    Column: id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: orders
    Column: status
    Type: enum('pending','processing','shipped','delivered','cancelled')
    Current Charset: utf8mb4
    Current Collation: utf8mb4_unicode_ci
-   Table: inventory
    Column: product_code
    Type: varchar(50)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: product_categories
    Column: description
    Type: text
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
-   Table: products
    Column: description
    Type: text
    Current Charset: utf8mb4
    Current Collation: utf8mb4_unicode_ci
-   Table: session_data
    Column: expires_at
    Type: timestamp
    Current Charset: None
    Current Collation: None
-   Table: product_images
    Column: product_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: audit_log
    Column: table_name
    Type: varchar(50)
    Current Charset: latin1
    Current Collation: latin1_swedish_ci
-   Table: audit_trail
    Column: changed_at
    Type: timestamp
    Current Charset: None
    Current Collation: None
-   Table: user_accounts
    Column: account_status
    Type: varchar(20)
    Current Charset: utf8mb4
    Current Collation: utf8mb4_general_ci
-   Table: orders_tinyint
    Column: order_id
    Type: tinyint(3) unsigned
    Current Charset: None
    Current Collation: None
-   Table: products
    Column: price
    Type: decimal(10,2)
    Current Charset: None
    Current Collation: None
-   Table: rank
    Column: score
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: customer_addresses
    Column: address_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: user_accounts
    Column: last_login
    Type: datetime
    Current Charset: None
    Current Collation: None
-   Table: product_images
    Column: image_id
    Type: int(11)
    Current Charset: None
    Current Collation: None
-   Table: customer_preferences
    Column: notification_settings
    Type: json
    Current Charset: None
    Current Collation: None

## Recommendations

### Pre-Upgrade Tasks
- Update parameter groups with recommended settings
- Take full backup of all databases
- Convert character sets to utf8mb4 where needed
- Make sure that the instance have enough resources (CPU, Memory, IOPS, storage) for the upgrade process
- Ensure there are no long-running transaction
- Make sure HLL is not high

### During Upgrade
- Follow upgrade order as specified
- Test each upgrade in non-production first
- Monitor replication lag during upgrades
- Verify application compatibility
- Have rollback plan ready

### Post-Upgrade Tasks
- Verify all stored procedures and views
- Check application performance
- Update monitoring and alerts
- Review and update backup strategies
- Document changes and lessons learned