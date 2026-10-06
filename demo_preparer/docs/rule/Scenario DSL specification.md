# Scenario DSL specification

constant

## Root Level DSL Object

```json
{
  "segments": [<Segment Parameter Sets>], 
  "parameters": { <Parameters> }, 
  "specification": { <Scenario Specification> },
}
```

## Segment Parameter Sets

When configuring a Scenario it is possible to define differing values, grouped by Segment, that are referenced at Evaluation time depending on the segment(s) that apply to the data being evaluated. 

To contain this configuration there is, at the root level of the Scenario DSL, a `segments` list. This list contains objects that;

- define the segment(s) `identifiers` to which the values inside it apply
- A `name` that is used in the UI to discern between segment parameter sets that are based on the same segment(s). 
- contain a `values` object which contains the `field_uuid` as a key and the value to be used for that field as the value. 
- contain an `outcome` object that contain the configuration required downstream when triggering actions within the system.
    - The `action` value is an ENUM of either `HOLD` or `ALLOW`
    - The `alert_priority` value is an integer from 1 to 9.

These `field_uuid`s will match with the `segment_parameter` value object defined in the Scenario Specification.

Some important notes about this configuration;

- A `segment_identifier` can be used in more than one `segments` definition
- Every `segment_parameter` value defined in the Scenario Specification **must** be represented in each `segments` definition
- When a Scenarios defines a `segments` configuration, the Evaluation Service will evaluate them synchronously in priority order - defined by their position in the list.

This `segments` root level object is required. You must supply it regardless of whether you have any `segment_parameters` as part of the Scenario Specification because it’s used to drive the outcome and alert priority.

```json
"segments": [
  {
    "identifiers": ["<segment_identifier>],
    "name": "All Customers A",
    "values": {
        "<field_uuid>": value // this maps to the segment value below
        "...": ...,  
      },
      "outcome": {
        "action": <HOLD|ALLOW>,
        "alert_priority": <1-9>.
      }
  },
  {...}
],
```


## Parameters

The `parameters` object provides a store for options that apply to the whole Scenario (are not configured per segment) and are required downstream of Evaluation, within the sync flow of Transaction Monitoring.

| **Key** | **Structure/Value** | **Notes** |
| --- | --- | --- |
| `risk_subject_grouping` | `"CUSTOMER\|COUNTERPARTY"` | Controls how Alerts generated from triggered Scenarios’s are grouped - either under Transaction, Customer, or Counterparty. |

## Scenario Specification

### **Operators**

| **Key** | **Structure** | **Allowed Children** |
| --- | --- | --- |
| Conditional Operators |  |  |
| `and` | `[   <object one>,   <object two>,   ... ]` | `and`, `or`, `not`, `equals`, `not_equals`, `greater_than`, `less_than`, `greater_than_or_equal`, `less_than_or_equal` |
| `or` |  |  |
| `not` | `[   <object one> ]` |  |
| Comparison Operators |  |  |
| `equals` | `[   <object one>,   <object two> ]` | `add`, `subtract`, `multiply`, `divide`, `mod`, `abs`, `field`, `segment`, `aggregation`, `constant`, `block` |
| `not_equals` |  |  |
| `greater_than` |  |  |
| `less_than` |  |  |
| `greater_than_or_equals` |  |  |
| `less_than_or_equals` |  |  |
| `any_of` | `[   <object one>,   <constant_list> ]` | `object one` : `add`, `subtract`, `multiple`, `divide`, `mod`, `abs`, `field`, `segment`, `aggregation`, `constant, block` |
| `not_any_of` | `constant list`: is required for `any_of` and `not_any_of` operators |  |
| Regex Operators |  |  |
| `regex_match` | `{   "regex_match": {     "text": { // needs to be type 'string'       "value": "customer[0].person.first_name",       "default": "Joe",       "datatype": "string",       "type": "field"     },     "pattern": "^.*[a-z]+$"   } }` | `text`: can be `block` , `constant`, `field`, and `segment_parameter` (must be of `datatype` “string”)`pattern`: a string with a valid regex pattern |
| Mathematical Operators |  |  |
| `add` | `[   <object one>,   <object two> ]` | `add`, `subtract`, `multiply`, `divide`, `mod`, `abs`, `field`, `segment`, `aggregation`, `constant`,`block` |
| `subtract` |  |  |
| `multiply` |  |  |
| `divide` |  |  |
| `mod` |  |  |
| `abs` | `[   <object one> ]` | same as above |

### **Values**

|  |  |
| --- | --- |
| **Type** | **Structure** |
| `constant` | `{   "type": "constant",   "value": "40",   "datatype": "number", // can be string or number   "name": "Amount Threshold" }` |
| `constant_list` | `{     "type": "constant_list",     "name": "Address Country",     "datatype": "string",     "values": ["ES", "FR", "IT"] }` |
| `field` | Standard transaction field`{   "type": "field",   "value": "transaction.monetary_details.direction",   "datatype": "string", // can be string or number   "default": "inbound" }`Custom transaction fields`{    "value": "transaction.custom_fields.your_field_name.string_value",    "default": null,    "datatype": "string",    "type": "field" } // or {    "value": "transaction.custom_fields.your_field_name.decimal_value",    "default": "0",    "datatype": "number",    "type": "field" }  `Standard customer record field`{   "type": "field",   "value": "customer[0].person.net_worth.float",    "datatype": "number",  // can be string or number   "default": "0" }`Enrichment field*keyed by enrichment* `key` *+ typed suffix* `string_value` / `decimal_value` / `boolean_value``{    "type": "field",   "value": "transaction.enrichments.your_enrichment_key.string_value",    "datatype": "string",   "default": null }`AI Detector score-bearing field`{   "type": "field",   "value": "detector.<detector_slug>.score",   "datatype": "number",   "default": 0 }`AI Detector scoreless field`{   "type": "field",   "value": "detector.<detector_slug>.triggered",   "datatype": "boolean",   "default": false }` |
| `segment_parameter` | `{   "type": "segment_parameter",   "value": "07275838-d961-4dde-bedf-c3ea789c0402"   "name": "Amount"   "format": "number", // this can be either string, number or boolean   "evaluated_value": 20 // this is set by the Evaluation Service only }` |
| `aggregation` | `{    "type": "aggregation",   "value": {      "uuid" : "2932e1f3-a33b-4ddc-8daf-b940d2f149b3",     "window" : 10, // Advise don't go over 2 years for performance/cost reasons          "window_unit": "day", // oneOf("year", "month", "day", "calendar_day", "hour", "minute")     "target_field": "amount", // not required for count, required for all others. 1 field only     "include_current_record" : true, // required     "exclude_current_day" : false, //required; can only set to true for "calendar_day" window_unit      "grouping_fields":     [       "transaction.monetary_details.direction",       {         "type": "block",         "value": "counterparty-id"       }     ],     "aggregate": "sum", // count, sum, average, average_count_over_day, max, min, variance, unique_count, std_dev.     "filter_spec": "<Logic defined using Scenario Specification>" // optional   },   "evaluated_value": 32 // this is set by the Evaluation Service only }` |
| `block` | `{   "type": "block",   "value": "example-slug",   "default": 3,   "datatype": "number" }` |

#### About blocks

Blocks are small, reusable components for extracting specific data points (e.g., customer age, transaction country). This will decouple our scenario logic from the underlying data structure, making it faster to build, easier to maintain, and simpler to test risk scenarios.

Each block is a bit of code that needs to be created by an engineer.

##### Example scenarios

```json
{
    "name": "Blocks example - find a specific counterparty using counterparty-id",
    "description": "Matches when the counterparty ID in the transaction is the same as the constant. Works when counterparty is the debtor or creditor",
    "specification": {
      "equals": [
        {
          "type": "block",
          "value": "counterparty-id",
          "datatype": "string",
          "default": "1234"
        },
        {
          "type": "constant",
          "value": "12-06-65-Johnson",
          "datatype": "string",
          "name": null,
        }
    ]
  }
}
```

```json
{
    "name": "Blocks example - find a specific counterparty using counterparty-details",
    "description": "Matches when the counterparty ID + name in the transaction is the same as the constant. Works when counterparty is the debtor or creditor",
    "specification": {
      "equals": [
        {
          "type": "block",
          "value": "counterparty-details",
          "datatype": "string"
        },
        {
          "type": "constant",
          "value": "353454354-Eric-Idle",
          "datatype": "string",
          "name": null,
        }
    ]
  }
}
```


#### Conditional Operators

- `and`, `or`, `not`
- Conditional operation typically take (but are not limited to)two inputs, with the exception of `not` which only takes one input. These inputs must resolve in a boolean so only Comparison Operators are valid children. 

```json
// Equivalent to "if operator1 is true and either operator2 or operator3 is true"
{
  "and": [
    <operator1>, 
    {
      "or": [
        <operator2>,
        <operator3>
      ]
    }
  ]
}
```

#### Comparison Operators:

- `equals`, `not_equals`, `greater_than`, `less_than`, `greater_than_or_equal`, `less_than_or_equal`
- Comparison Operators only accept 2 inputs, which must resolve in a value that can be compared. Therefore, the only valid children of Comparions Operators are Mathematical Operators or Values. 

```json
"equals" : [
  <object one>,
  <object two>
]

"less_than" : [
  <object one>,
  <object two>
]

"equals" : [
  <object one>,
   {
   "multiply" : [
    <object one>,
    <object two>
    ]
  }
]

"greater_than" : [
  {
    "divide" : [
      <object one>,
      <object two>
    ]
  },
  {
   "multiply" : [
      <object one>,
      <object two>
    ]
  }
]
```


#### Regex Operators

- `regex_match`
- `regex_match` functions as a comparison operator, so it can be used as a top-level operator in a scenario specification, and can be combined with other comparison operators using conditional operators like `and`.
- its `text` parameter can be any operator that resolves to a string
- its `pattern` parameter is a string representing a valid regex pattern
- case insensitivity can be achieved by appending `(?i)` to the `pattern` string

Example:

```
"regex_match": {
  "text": {
    "value": "transaction.monetary_details.bank_payment.debtor.name",
    "default": "Joe",
    "datatype": "string",
    "type": "field"
  },
  "pattern": "(?i)Joe"
}
```

#### Combining Conditional, Comparison and Mathematical Operators:

- Conditional operators `and` , `or` and `not` can then be used to chain these comparison operators.

```json
"or" : [
  {
    "greater_than" : [
      {
        "divide" : [
          <object one>,
          <object two>
        ]
      },
      {
        "multiply" : [
          <object one>,
          <object two>
        ]
      }
    ]
  },
  {
    "less_than_or_equal" : [
      {
        "divide" : [
          <object one>,
          <object two>
        ]
      },
      {
        "multiply" : [
          {
            "add" : [
              <object one>,
              <object two>
            ]
          },
          {
            "subtract" : [
              <object one>,
              <object two>
            ]
          }
        ]
      }
    ]
  }
]
```

- Conditional operators can also be chained together to form further relationships and complexity.

```json
"and" : [
  {
    "greater_than" : [
      {
        "divide" : [
          <object one>,
          <object two>
        ]
      },
      {
        "multiply" : [
          <object one>,
          <object two>
        ]
      }
    ],
  },
  {
    "or" : [
      {
        "greater_than" : [
          {
            "divide" : [
              <object one>,
              <object two>
            ]
          },
          {
            "multiply" : [
              <object one>,
              <object two>
            ]
          }
        ]
      },
      {
        "less_than_or_equal" : [
          {
            "divide" : [
              <object one>,
              <object two>
            ]
          },
          {fi
            "multiply" : [
              {
                "add" : [
                  <object one>,
                  <object two>
                ]
              },
              {
                "subtract" : [
                  <object one>,
                  <object two>
                ]
              }
            ]
          }
        ]
      }
    ]
  }
]
```

- In theory, there is no limit to the number of chained conditional operators, and this in turn extends to the comparison and mathematical operators also. 


#### Representing the variables and aggregations in the request

A simple comparison operation will only have two inputs, these being either variables (either values on the transaction, or predefined segment values) or additional data retrieved from services such as aggregation service. 

```json
"equals" : [
  <object one>,
  <object two>
]
```

These values will correspond to a type, such as but not limited to - `aggregation`, `segment` or `field` - or the output of another mathematical expression.

### Data Types

The values processed as part of a scenario have a specified data type. In a field operator, for example, this is defined by the `datatype` parameter:

```
{
  "type": "field",
  "value": "transaction.monetary_details.direction",
  "datatype": "string",
  "default": "inbound"
}
```

These data types will define what operations can be performed on them. It’s not possible, for example, to perform a comparison between different data types:

```
"specification":{ // not valid because it compares a string with an integer
   "equals":[
      {
         "value":"transaction.monetary_details.value.amount",
         "default":"10",
         "datatype":"number",
         "type":"field"
      },
      {
         "value":"hello",
         "datatype":"string",
         "name":null,
         "type":"constant"
      }
   ]
}
```

or to perform mathematical operations on not numeric values:

```
"subtract": [ // not valid because it performs a math operation on strings
  {
    "value": "transaction.monetary_details.value.iso_3_currency_code",
    "default": "EUR",
    "datatype": "string",
    "type": "field"
  },
  {
    "value": "hello",
    "datatype": "string",
    "name": null,
    "type": "constant"
  }
]
```


#### Available Data Types

Below are the existing valid data types

| **Data Type** | **Examples** | **Restrictions** |
| --- | --- | --- |
| `number` | - `1` - `0` - `0.1` - `-2.54` | Used on mathematical and comparison operators. Can only be used against other numbers. |
| `string` | - `hello` - `a string` | Cannot be used on mathematical operations. Can be used on comparison operators only against other strings. |
| `date` | Must follow [ISO 8601](https://www.iso.org/iso-8601-date-and-time-format.html) - `2020-01-02` | Can be used on comparison operators only against other dates.Can be used on subtractions agains other dates, but not on any other mathematical operators. |
| `datetime` | Must follow [ISO 8601](https://www.iso.org/iso-8601-date-and-time-format.html) - `2020-01-02T12:00:04.20Z` - `2020-10-10T12:10:20.0045+08:00` | Can be used on comparison operators only against other datetimes.Can be used on subtractions agains other datetimes, but not on any other mathematical operators. |
| `boolean` | Case insensitive - `true` - `false` - `True` - `faLse` | Can only be used in `Equals` and `Not Equals` operators against other booleans. |

#### Type conversion

The `date` and `datetime` data types can be converted between them at evaluation level.

By providing the desired type as the `datatype` parameter the system will know to coerce either the `date` to `datetime`, or vice-versa.

The following example is valid even though `date_of_birth` is a `date`:

```
"equals": [
  {
    "value": "customer[0].person.date_of_birth",
    "default": "2020-10-10T10:20:30Z",
    "datatype": "datetime",
    "type": "field"
  },
  {
    "value": "2020-10-10T10:20:30Z",
    "datatype": "datetime",
    "name": null,
    "type": "constant"
  }
]
```

Type conversions work by either removing the time component from a `datetime`, or adding the time `00:00:00` to a given `date`.

Type conversions are not supported for any other data types.


### Values

#### Evaluated Values

Protobuf schemas for the `field`, `segment_parameter` and `aggregation` Value Operators contain an `evaluated_values` key. This key is used by the Scenario Evaluation service so that downstream services know which exact values we used during the evaluation of a Scenario

**This field should not be set during Scenario Template or Instance configuration.**

#### Constants:

Constants are values that don’t need to be looked up at Evaluation Time. 

```json
// constant
{
  "type": "constant",
  "value": 300,
  "datatype": "number",
  "name": "Amount Threshold",
}
```

**Fields:**

The `value` corresponds to the path within the supplied data from which to get the input. During Evaluation the value will be fetched from the location specified to be used. If the key specified in `value` doesn’t exist in the supplied data then the `default` value will be used instead

**If the value cannot be found in the supplied data, and there is no default specified, then the Evaluation halts and an Error is thrown.**

```json
// field data
{
  "type": "field",
  "value": "customer.account.balance",
  "datatype": "number",
  "default": 100,
  "evaluated_value": 403 // this is set by the Evaluation Service only
}
```

The following path namespaces can be used in Fields.

| Namespace | Contains | Example path |
| --- | --- | --- |
| `transaction.*` | incl. `transaction.custom_fields.*` and `transaction.enrichments.*` | `transaction.monetary_details.value.amount` |
| `customer[N].*` | the customer record(s) | `customer[0].person.net_worth.float` |
| `detector.*` | AI detector results (FRD-143), keyed by detector slug | `detector.<slug>.score``detector.<slug>.triggered` |

**Segment Parameters:**

Used in conjunction with the root level `segments` object - the UUID specified in the `value` is used during Evaluation time to map to a value (according to the provided Segment). 

Like Constants, Segment Parameter’s also contain `name` and `format` which are used to identify the field within the Scenario, and validate the user input. 

```json
// segment parameter
{
  "type": "segment_parameter",
  "value": "07275838-d961-4dde-bedf-c3ea789c0402",
  "name": "Amount Threshold",
  "format": "number",
  "evaluated_value": 30 // this is set by the Evaluation Service only
}
```

**Aggregation**

The Aggregation value type serves 2 (or 3) purposes;

1. The `uuid` value in the `value` object is the Aggregator Query Identifier, and is used to map to the value in the Aggregated Data supplied alongside Activity Data at evaluation time
2. The other values stored within the DSL are sent to the Aggregation Service in order for it to create the required Aggregation. 
    1. And it is also how the UI know what kind of Aggregated Data is going to be used within a Scenario

```json
// aggregation
{ 
  "type": "aggregation",
  "value": { 
    "uuid" : 2932e1f3-a33b-4ddc-8daf-b940d2f149b3",
    "window" : 10,
    "window_unit": "day",
    "target_field": "amount",
    "include_current_record" : True,
    "exclude_current_day" : False,
    "grouping_fields": ["country","tx_direction"],
    "aggregate": "sum",
    "filter_spec": "<Logic defined using Scenario Specification>"
  },
  "evaluated_value": 34 // this is set by the Evaluation Service only
}
```

Aggregation `type` can either be `scalar` or `HLL`[ (HyperLogLog)](https://en.wikipedia.org/wiki/HyperLogLog)

#### Scenario Example 1:

```json
// Template (post release 1)
{
  "segments": [],
  "specification": {
    "equals" : [
      {
        "type": "segment",
        "value": "2932e1f3-a33b-4ddc-8daf-b940d2f149b3"
        "name": "Value"
        "format": "number",
      },
      { 
        "type": "aggregation",
        "value": { 
          "uuid" : "2932e1f3-a33b-4ddc-8daf-b940d2f149b3",
          "window" : 10,
          "window_unit": "day",
          "target_field": "amount",
          "include_current_record" : True,
          "exclude_current_day" : False,
          "grouping_fields": ["country","tx_direction"],
          "aggregate": "sum",
          "filter_spec": "<Logic defined using Scenario Specification>",
        }
      }
    ]
  }
}

// Instance
{
  "segments": [
    {
      "segment_identifiers": ["07275838-d961-4dde-bedf-c3ea789c0403"], 
      "name": "High Risk"
      "values": {
        "2932e1f3-a33b-4ddc-8daf-b940d2f149b3": 1000,
      },
      "outcome": {
        "action": "HOLD",
        "alert_priority": 1.
      }
    },
    {
      "segment_identifiers": ["07275838-d961-4dde-bedf-c3ea789c0402"], 
      "name": "Low Risk"
      "values": {
        "2932e1f3-a33b-4ddc-8daf-b940d2f149b3": 3000,
      },
      "outcome": {
        "action": ALLOW,
        "alert_priority": 5.
      }
    }
  ],
  "specification": {
    "equals" : [
      {
        "type": "segment",
        "value": "2932e1f3-a33b-4ddc-8daf-b940d2f149b3",
        "name": "Value"
        "format": "number",
      },
      { 
        "type": "aggregation",
        "value": { 
          "window" : 10,
          "window_unit": "day",
          "target_field": "amount",
          "include_current_record" : True,
          "exclude_current_day" : False,
          "grouping_fields": ["country","tx_direction"],
          "type": "scalar",
          "aggregate": "sum",
          "filter_spec": "<Logic defined using Scenario Specification>",
        }
      }
    ]
  }
}
```

#### Example request schema for evaluation (WIP): 

```json
{
  "scenario_identifiers" : ["0e790ca1-6aab-4e1d-9876-6d28a30db944"],
  "segments": ["07275838-d961-4dde-bedf-c3ea789c0402"],
  "data" : {
    "aggregation" : [
      {
        "uuid" : "2932e1f3-a33b-4ddc-8daf-b940d2f149b3",
        "value" : 100
      }
    ],
    "fields " : [
      ...
    ]
  }
}
```

#### Scenario Example 2:

```
{
  "segments": [
      {
      "identifiers": ["<segment_id_for_all_customers>"], 
      "name": "All Customers",
      "values": {
      },
      "outcome": {
        "action": "HOLD",
        "alert_priority": 3
      }
    }
  ],
  "specification": {
    "greater_than" : [
      {
        "type": "field",
        "value": "customer.person.salary_range.high",
        "datatype": "number",
        "default": 30000
      },
      { 
        "type": "aggregation",
        "value": { 
          "window" : 10,
          "window_unit": "month",
          "target_field": "amount",
          "include_current_record" : True,
          "exclude_current_day" : False,
          "grouping_fields": ["country","tx_direction"],
          "type": "scalar",
          "aggregate": "sum",
          "filter_spec": "<Logic defined using Scenario Specification>",
        }
      }
    ]
  }
}
```

#### Scenario Example 3:

```
{
  "segments": [
    {
      "identifiers": ["<all_segments_uuid>"], 
      "name": "All Customers",
      "values": {},
      "outcome": {
        "action": "HOLD",
        "alert_priority": 3
      }
    }
  ],
  "parameters": {
    "risk_subject_grouping": "TRANSACTION"
  },
  "specification": {
    "greater_than" : [
      { 
        "type": "aggregation",
        "value": { 
          "uuid" : "a1a1a1a1-1111-4111-8111-a1a1a1a1a1a1",
          "window" : 7,
          "window_unit": "day",
          "target_field": "customer_id", 
          "include_current_record" : true,
          "exclude_current_day" : false,
          "grouping_fields": [],
          "type": "HLL",
          "aggregate": "count"
        },
      },
      {
        "type": "constant",
        "value": 1500,
        "datatype": "number",
        "name": "Unique Customer Threshold",
      }
    ]
  }
}
```

#### Scenario Example 4:

```
{
  "segments": [
    {
      "segment_identifiers": ["07275838-d961-4dde-bedf-c3ea789c0403"], 
      "name": "High Risk"
      "values": {
        "2932e1f3-a33b-4ddc-8daf-b940d2f149b3": 1000,
      },
      "outcome": {
        "action": "HOLD",
        "alert_priority": 1.
      }
    },
    {
      "segment_identifiers": ["07275838-d961-4dde-bedf-c3ea789c0402"], 
      "name": "Low Risk"
      "values": {
        "2932e1f3-a33b-4ddc-8daf-b940d2f149b3": 3000,
      },
      "outcome": {
        "action": ALLOW,
        "alert_priority": 5.
      }
    }
  ],
  "specification": {
    "greater_than" : [
      { 
        "type": "aggregation",
        "value": { 
          "uuid" : "c3c3c3c3-3333-4333-8333-c3c3c3c3c3c3",
          "window" : 24,
          "window_unit": "hour",
          "include_current_record" : true,
          "exclude_current_day" : false,
          "grouping_fields": ["customer_id"],
          "type": "scalar",
          "aggregate": "count"
        }
      },
      {
        "type": "segment_parameter",
        "value": "2932e1f3-a33b-4ddc-8daf-b940d2f149b3",
        "name": "Max Daily Transaction Count",
        "format": "number"
      }
    ]
  }
}
```

## Real-life Examples

### AnyOf and NotAnyOf operators

**Base example:**

`any_of`/ `not_any_of`:

```json
"any_of": [
  {
    "value": "transaction.monetary_details.base_value.iso_3_currency_code",
    "default": "N/a",
    "datatype": "string",
    "type": "field"
  },
  {
    "name": "Currency",
    "values": [
      "usd",
      "eur"
    ],
    "datatype": "string",
    "type": "constant_list"
  }
]
```

# Blocks

## calendar-month

Returns the calendar month of the `occurred_at` field for the transaction.

Values: 1,2,3,4 etc
