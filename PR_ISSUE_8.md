# PR: Template Marketplace with RTC Pricing - Issue #8

## Summary
This PR implements a complete **template marketplace** with **RTC token pricing** for the ShaprAI ecosystem. Users can now publish, buy, sell, and rate agent templates using RTC tokens.

## Features Implemented

### 1. Template Marketplace Core (`shaprai/core/template_engine.py`)

#### New Data Classes
- **`MarketplaceTemplate`**: Represents a template listing with pricing, author, ratings, and download stats

#### New Functions
- **`publish_template()`**: Publish a template to the marketplace with RTC pricing
- **`purchase_template()`**: Buy a template with automatic RTC payment processing
- **`list_marketplace_templates()`**: Browse all available templates
- **`rate_template()`**: Rate purchased templates (1.0-5.0 stars)
- **`_process_template_payment()`**: Internal payment processing helper

### 2. RustChain RTC Integration (`shaprai/integrations/rustchain.py`)

#### New Constants
- **`TEMPLATE_LISTING_FEE = 0.005 RTC`**: Fee to list a template
- **`TEMPLATE_SALE_ROYALTY = 0.02 (2%)`**: Platform royalty on sales

#### New Functions
- **`pay_template_listing_fee()`**: Pay the marketplace listing fee
- **`process_template_sale()`**: Process template sale with automatic royalty split
  - Seller receives: `price * 0.98`
  - Platform receives: `price * 0.02` (royalty)
- **`get_template_sales_history()`**: Get sales history for a seller

### 3. CLI Commands (`shaprai/cli.py`)

New `shaprai marketplace` command group:

```bash
# List all marketplace templates
shaprai marketplace list

# Publish a template
shaprai marketplace publish <template_name> --price 5.0 --author "my_name"

# Purchase a template
shaprai marketplace purchase <template_name> --wallet "my-wallet-id"

# Rate a purchased template
shaprai marketplace rate <template_name> --rating 4.5

# Check wallet balance
shaprai marketplace balance --wallet "my-wallet-id"
```

## Architecture

### Marketplace Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Seller    │────▶│  Marketplace │◀────│    Buyer    │
│             │     │   Listing    │     │             │
└─────────────┘     └──────────────┘     └─────────────┘
       │                   │                    │
       │ 1. Publish        │                    │
       │    (pay 0.005 RTC)│                    │
       ├──────────────────▶│                    │
       │                   │                    │
       │                   │ 2. Browse          │
       │                   │◀───────────────────┤
       │                   │                    │
       │                   │ 3. Purchase        │
       │                   │◀───────────────────┤
       │                   │                    │
       │                   │ 4. Process Payment │
       │                   │    (2% royalty)    │
       │◀──────────────────┼───────────────────▶│
       │ 98% of price      │                    │ 100% of price
       │                   │                    │
```

### File Structure

```
~/.shaprai/marketplace/
├── <template_name>.yaml          # Template file
├── <template_name>.listing.yaml  # Listing metadata (price, author, rating)
└── ...
```

### Listing Metadata Format

```yaml
name: bounty_hunter
author: elyan_labs
description: Autonomous bounty hunter for GitHub bounties
price_rtc: 5.0
version: "1.0"
capabilities:
  - code_review
  - bounty_discovery
downloads: 0
rating: 0.0
created_at: 1710316800.0
updated_at: 1710316800.0
```

## Testing

### Test Coverage: 20 Tests Passed ✅

**Test File**: `tests/test_marketplace.py`

#### Test Categories:
1. **PublishTemplate** (3 tests)
   - Template publishing creates files
   - YAML content validation
   - Listing metadata validation

2. **ListMarketplaceTemplates** (3 tests)
   - Empty marketplace handling
   - Multiple templates listing
   - Malformed listing skip

3. **RateTemplate** (3 tests)
   - Single rating update
   - Multiple ratings average
   - Nonexistent template handling

4. **PurchaseTemplate** (3 tests)
   - Successful purchase
   - Payment failure handling
   - Nonexistent template handling

5. **TemplatePayment** (2 tests)
   - Payment processing success
   - Payment processing failure

6. **RustChainMarketplaceFunctions** (4 tests)
   - Fee constant validation
   - Royalty rate validation
   - Listing fee payment
   - Sale with royalty split

7. **MarketplaceTemplateDataclass** (2 tests)
   - Default values
   - Capabilities and metadata

### Run Tests
```bash
cd shaprai
pytest tests/test_marketplace.py -v
```

## Usage Examples

### 1. Publish a Template

```bash
# Create a template first
shaprai template create my_template --model Qwen/Qwen3-7B-Instruct --description "My awesome template"

# Publish to marketplace
shaprai marketplace publish my_template --price 5.0 --author "john_doe"
```

**Output:**
```
Template 'my_template' published to marketplace!
  Author: john_doe
  Price: 5.000 RTC
  Listing fee: 0.005 RTC (paid)
  Wallet: agent-john_doe
```

### 2. Browse Marketplace

```bash
shaprai marketplace list
```

**Output:**
```
Name                      Author               Price (RTC)     Rating
--------------------------------------------------------------------------------
bounty_hunter             elyan_labs           5.000           ⭐ 4.5
code_reviewer             elyan_labs           3.000           New
my_template               john_doe             5.000           ⭐ 4.0

Total: 3 template(s)
```

### 3. Purchase a Template

```bash
shaprai marketplace purchase bounty_hunter --wallet "shaprai-my-agent"
```

**Output:**
```
Your balance: 10.500 RTC
✅ Successfully purchased 'bounty_hunter'!
  Description: Autonomous bounty hunter — discovers, claims, and delivers GitHub bounties for RTC
  Capabilities: code_review, pr_submission, bounty_discovery, issue_triage, test_writing
  Model: Qwen/Qwen3-7B-Instruct
```

### 4. Rate a Template

```bash
shaprai marketplace rate bounty_hunter --rating 5.0
```

**Output:**
```
✅ Rated 'bounty_hunter' with 5.0 stars!
```

## Economic Model

### Fee Structure
| Action | Fee | Recipient |
|--------|-----|-----------|
| List template | 0.005 RTC | Marketplace treasury |
| Purchase template | 2% royalty | Marketplace treasury |
| Template sale | 98% of price | Template author |

### Example Transaction
For a template priced at **10 RTC**:
- **Buyer pays**: 10 RTC
- **Seller receives**: 9.8 RTC (98%)
- **Platform receives**: 0.2 RTC (2% royalty)

## Acceptance Criteria Met

- ✅ **Template marketplace functionality implemented**
  - Publish templates with pricing
  - Browse available templates
  - Purchase templates with RTC
  - Rate purchased templates

- ✅ **RTC pricing system implemented**
  - Listing fees (0.005 RTC)
  - Sale royalties (2%)
  - Automatic payment splitting
  - Wallet balance checking

- ✅ **All tests pass** (20/20)
- ✅ **Integration with existing RustChain economy**
- ✅ **CLI commands for all marketplace operations**
- ✅ **Comprehensive test coverage**

## Files Modified

1. `shaprai/core/template_engine.py` - Marketplace core logic
2. `shaprai/integrations/rustchain.py` - RTC payment processing
3. `shaprai/cli.py` - CLI commands

## Files Added

1. `tests/test_marketplace.py` - Comprehensive test suite
2. `PR_ISSUE_8.md` - This PR description

## Backward Compatibility

✅ All changes are backward compatible:
- Existing template functionality unchanged
- New marketplace features are additive
- No breaking changes to existing APIs

## Future Enhancements

Potential improvements for future PRs:
- Template search and filtering
- Featured templates section
- Bundle deals (multiple templates)
- Subscription-based template access
- Template preview before purchase
- Author verification system
- Dispute resolution mechanism

## Related Issue

Closes #8: [BOUNTY: 40 RTC] Template marketplace with RTC pricing
