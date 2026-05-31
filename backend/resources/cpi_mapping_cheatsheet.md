# SAP CPI Graphical Message Mapping — Complete Reference

> Used by AI when generating .mmap files, XSDs, and mapping rules.

---

## PART 1: CONTEXT — The Most Critical Concept

### What is Context?

Context in SAP CPI determines "how many times" a mapping executes and "at what level"
of the XML hierarchy. Every element in the source XML has a context determined by its
maxOccurs setting and its parent chain.

### Context Example

```xml
<SalesOrder>                      <!-- context level 1 (occurs once) -->
  <OrderID>SO123</OrderID>        <!-- context 1: one value -->
  <Items>
    <Item>                        <!-- context level 2 (repeating, 1..N) -->
      <ProductID>A</ProductID>    <!-- context 2: one per Item -->
      <Quantity>5</Quantity>      <!-- context 2: one per Item -->
      <Price>10.00</Price>        <!-- context 2: one per Item -->
    </Item>
    <Item>
      <ProductID>B</ProductID>
      <Quantity>3</Quantity>
      <Price>20.00</Price>
    </Item>
  </Items>
</SalesOrder>
```

### Context Rules

| Cardinality change | Pattern | Functions to use |
|--------------------|---------|-----------------|
| N → 1 (aggregate) | Sum all item quantities into one total | sum(), average(), count() |
| 1 → N (expand) | Repeat order date on every item line | useOneAsMany() |
| N → N (same level) | Copy each item field to matching target | direct copy or transform |
| N → 1 (collapse text) | Merge all product IDs into one string | collapseContexts() |

### Context Pattern Examples

#### Pattern 1: Direct 1:1 (same context)
```
Source: /Order/Items/Item/Quantity  (context 2)
Target: /Summary/Items/Item/Qty     (context 2)
→ DIRECT COPY, no function needed
```

#### Pattern 2: Sum N→1 (aggregate)
```
Source: /Order/Items/Item/Quantity  (context 2, repeating)
Target: /Summary/TotalQuantity      (context 1, single)
→ sum((/Order/Items/Item/Quantity))
```

#### Pattern 3: Repeat 1→N (expand)
```
Source: /Order/OrderDate            (context 1, single)
Target: /Summary/Items/Item/Date    (context 2, one per item)
→ useOneAsMany((/Order/OrderDate))
```

#### Pattern 4: Concatenate repeating values into single
```
Source: /Order/Items/Item/ProductID (context 2, repeating)
Target: /Summary/AllProducts        (context 1, single)
→ collapseContexts((/Order/Items/Item/ProductID))
```

#### Pattern 5: Count occurrences
```
Source: /Order/Items/Item           (context 2)
Target: /Summary/ItemCount          (context 1)
→ count((/Order/Items/Item))
```

#### Pattern 6: Sequential line numbering
```
Source: /Order/Items/Item/ProductID (context 2)
Target: /Output/Item/LineNumber     (context 2)
→ index((/Order/Items/Item/ProductID))   -- returns 0, 1, 2, 3 ...
```

---

## PART 2: COMPLETE FUNCTION REFERENCE

### 2.1 ARITHMETIC

| fname | User writes | Description | Bindings |
|-------|-------------|-------------|---------|
| add | add((/f1), (/f2)) | Add two values | none |
| subtract | subtract((/f1), (/f2)) | Subtract | none |
| multiply | multiply((/f1), (/f2)) | Multiply | none |
| divide | divide((/f1), (/f2)) | Divide | none |
| abs | absolute((/f)) or abs((/f)) | Absolute value | none |
| neg | neg((/f)) | Negate (-x) | none |
| inv | inv((/f)) | Inverse (1/x) | none |
| sqrt | sqrt((/f)) | Square root | none |
| sqr | square((/f)) or sqr((/f)) | Square (x^2) | none |
| sign | sign((/f)) | Sign: 1, 0, or -1 | none |
| power | power((/base), (/exp)) | base^exponent | none |
| less | lesser((/f1), (/f2)) | true if f1 < f2 | none |
| greater | greater((/f1), (/f2)) | true if f1 > f2 | none |
| max | max((/f1), (/f2)) | Maximum of two values | none |
| min | min((/f1), (/f2)) | Minimum of two values | none |
| ceil | ceil((/f)) | Round up | none |
| floor | floor((/f)) | Round down | none |
| round | round((/f)) | Round to nearest integer | none |
| equalsA | equals((/f), NUMBER) | Numeric equality | none |
| counter | counter(start, increment) | Incrementing counter | start, increment |
| FormatNum | formatNumber((/f), PATTERN) | Format number e.g. 0.00 | format |

### 2.2 BOOLEAN

| fname | User writes | Description |
|-------|-------------|-------------|
| Equals | equals((/f), VALUE) | Equality comparison (boolean) |
| notEquals | notEquals((/f), VALUE) | Inequality |
| And | and((/b1), (/b2)) | Logical AND |
| Or | or((/b1), (/b2)) | Logical OR |
| Not | not((/b)) | Logical NOT |
| if | if((/cond), trueVal, falseVal) | Conditional — 3 source args |
| ifS | ifS((/f), compareVal, trueVal, falseVal) | If with string compare |
| ifWithoutElse | ifWithoutElse((/cond), trueVal) | If without else |
| ifSWithoutElse | ifSWithoutElse((/f), compareVal, trueVal) | IfS without else |
| isNil | isNil((/f)) | True if value is xsi:nil |

**IMPORTANT:** `equals` → real fname is `Equals` (capital E)

### 2.3 CONSTANT

| fname | User writes | Description |
|-------|-------------|-------------|
| constant | constant(VALUE) | Emit a fixed constant value — no source field required |
| copyValue | copyValue((/f)) | Copy source value as-is |
| xsi:nil | xsi:nil | Emit xsi:nil="true" for the target element |

### 2.4 CONVERSION

| fname | User writes | Description |
|-------|-------------|-------------|
| fixValues | fixValues((/f)) | Fixed value lookup table (key→value pairs defined in the brick) |
| valuemap | valueMapping((/f)) | Value Mapping table lookup (CPI Value Mapping artifact) |

### 2.5 DATE

| fname | User writes | Bindings |
|-------|-------------|---------|
| TransformDate | formatDate((/f), iFmt, oFmt) | iform, oform, calend |
| currentDate | currentDate() | No source arg |
| DateBefore | DateBefore((/d1), (/d2)) | Two date source args |
| DateAfter | DateAfter((/d1), (/d2)) | Two date source args |
| CompareDates | CompareDates((/d1), (/d2)) | Returns 1, 0, -1 |

**IMPORTANT:** `formatDate` is a user alias — the real fname is `TransformDate`

Date format tokens: `yyyyMMdd`, `yyyy-MM-dd`, `dd.MM.yyyy`, `HHmmss`, `HH:mm:ss`, `yyyy-MM-dd'T'HH:mm:ss`

### 2.6 NODE FUNCTIONS

| fname | User writes | Description | Context effect |
|-------|-------------|-------------|---------------|
| createIf | createIf((/cond)) | Create target element only if condition is true | conditional |
| removeContexts | removeContexts((/f)) | Flatten hierarchy to a flat list | removes levels |
| replaceValue | replaceValue((/f)) | Replace with a configured value | none |
| exists | exists((/f)) | True if field has a non-nil value | none |
| getHeader | getHeader(HEADER_NAME) | Get message header value by name | none |
| getProperty | getProperty(PROP_NAME) | Get integration flow property by name | none |
| SplitByValue | SplitByValue((/f), DELIM) | Split value into multiple occurrences | creates context |
| collapseContexts | collapseContexts((/f)) | Merge N contexts into 1 | N→1 |
| useOneAsMany | useOneAsMany((/f)) | Repeat a single value for each target occurrence | 1→N |
| sort | sort((/f)) | Sort values ascending | preserves context count |
| sortByKey | sortByKey((/f)) | Sort by key | preserves context count |
| mapWithDefault | mapWithDefault((/f), DEFAULT) | Pass value or emit default if empty | none |
| formatByExample | formatByExample((/format), (/data)) | Apply format pattern from example | none |

### 2.7 STATISTICS (Aggregate — operate on the ENTIRE context queue)

| fname | User writes | Description | Context effect |
|-------|-------------|-------------|---------------|
| sum | sum((/f)) | Sum ALL occurrences — e.g. total of all Item/Quantity | N→1 |
| average | average((/f)) | Average of all values | N→1 |
| count | count((/f)) | Count of occurrences | N→1 |
| index | index((/f)) | 0-based index of each occurrence | preserves N |
| first | first((/f)) | First value in the queue | N→1 |
| last | last((/f)) | Last value in the queue | N→1 |

**DO NOT use Groovy UDF for sum/average/count — use Statistics functions!**

### 2.8 TEXT (STRING)

| fname | User writes | Bindings |
|-------|-------------|---------|
| toUpperCase | toUpperCase((/f)) | none |
| toLowerCase | toLowerCase((/f)) | none |
| trim | trim((/f)) | none |
| length | length((/f)) | none |
| concat | (/f1)+SEP+(/f2) | delimeter=SEP |
| substring | substring((/f), 0, 5) | from, to |
| replaceString | replaceAll((/f), old, new) | search, replace |
| SplitByValue | SplitByValue((/f), ,) | delimeter |
| indexOf | indexOf((/f), text) | search |
| indexOf (3-arg) | indexOf((/f), text, startPos) | search, from |
| lastIndexOf | lastIndexOf((/f), text) | search |
| lastIndexOf (3-arg) | lastIndexOf((/f), text, startPos) | search, from |
| compare | compare((/f1), (/f2)) | none |
| equalsS | equals((/f), STRING) | none |
| endsWith | endsWith((/f), suffix) | value |
| startsWith | startsWith((/f), prefix) | value |
| startsWith (3-arg) | startsWith((/f), prefix, pos) | value, from |
| contains | contains((/f), text) | search |
| copyValue | copyValue((/f)) | none |

---

## PART 3: ZIP BUNDLE STRUCTURE

```
mapping/<MappingName>.mmap    <- the mapping XML (REQUIRED)
wsdl/<source_xsd_name>.xsd    <- source schema (REQUIRED)
wsdl/<target_xsd_name>.xsd    <- target schema (REQUIRED, if different name)
```

**Critical rules:**
- XSDs go in `wsdl/` folder (NOT `xsd/` or root)
- .mmap goes in `mapping/` folder
- No MANIFEST.MF or .project needed for download (added by API import layer)

---

## PART 4: .MMAP XML STRUCTURE (urn:sap-com:xi format)

```xml
<?xml version="1.0" encoding="utf-8"?>
<xiObj xmlns="urn:sap-com:xi">
  <idInfo VID="01">
    <vc caption="LOCAL" sp="-1" swcGuid="00000000000000000000000000000000" vcType="S">
      <clCxt consider="A"/>
    </vc>
    <key typeID="XI_TRAFO" version=""/>
    <version>1.0</version>
  </idInfo>
  <documentation><description/></documentation>
  <generic>
    <admInf>
      <modifBy></modifBy><modifAt></modifAt>
      <modifAtLong>TIMESTAMP_MS</modifAtLong>
      <owner/>
    </admInf>
    <lnks>
      <!-- TARGET comes FIRST -->
      <lnkRole kpos="1" role="TARGET_IFR_MESS">
        <lnk rMode="R">
          <key typeID="xsd" version="1.1">
            <elem>target.xsd</elem>
            <elem>src/main/resources/wsdl</elem>
            <elem>RootElementName</elem>  <!-- MUST match xs:element name in XSD -->
          </key>
        </lnk>
      </lnkRole>
      <!-- SOURCE comes SECOND -->
      <lnkRole kpos="1" role="SOURCE_IFR_MESS">
        <lnk rMode="R">
          <key typeID="xsd" version="1.1">
            <elem>source.xsd</elem>
            <elem>src/main/resources/wsdl</elem>
            <elem>RootElementName</elem>
          </key>
        </lnk>
      </lnkRole>
    </lnks>
  </generic>
  <content>
    <tr:XiTrafo xmlns:tr="urn:sap-com:xi:mapping:xitrafo">
      <tr:MetaData>
        <mappingtool version="XI7.1">
          <project version="XI7.1">
            <transformation>
              <!-- ALL MAPPING BRICKS GO HERE -->
            </transformation>
          </project>
        </mappingtool>
      </tr:MetaData>
      <tr:ByteCodeJar/>
      <tr:SourceStructure/><tr:TargetStructure/>
      <tr:Multiplicity>1:1</tr:Multiplicity>
    </tr:XiTrafo>
  </content>
</xiObj>
```

### Brick XML Format (confirmed from real CPI exports)

**Direct mapping (source to target, no transformation):**
```xml
<brick gid="0" path="/Target/Root/FieldName" type="Dst">
  <viewData x="200" y="40"/>
  <arg>
    <brick gid="0" path="/Source/Root/FieldName" type="Src">
      <viewData x="50" y="40"/>
    </brick>
  </arg>
  <group/>
</brick>
```

**Function brick (transformation):**
```xml
<brick gid="0" path="/Target/Root/Field" type="Dst">
  <viewData x="200" y="40"/>
  <arg>
    <brick fname="FUNCTION_NAME" fns="dflt" type="Func">
      <viewData x="125" y="30"/>
      <arg>
        <brick gid="0" path="/Source/Root/Field" type="Src">
          <viewData x="50" y="30"/>
        </brick>
      </arg>
      <bindings>
        <param name="PARAM_NAME"><value>PARAM_VALUE</value></param>
      </bindings>
    </brick>
  </arg>
  <group/>
</brick>
```

**Key rules:**
- Function bricks use `fname` + `fns="dflt"` + `type="Func"`
- First arg: `<arg>` (no pin attribute)
- Subsequent args: `<arg pin="1">`, `<arg pin="2">` etc.
- Parameters go in `<bindings>` not as separate arg bricks

---

## PART 5: XSD RULES

### Correct XSD (CPI-compatible)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Order">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="OrderId"      type="xs:string"  minOccurs="0"/>
        <xs:element name="OrderDate"    type="xs:string"  minOccurs="0"/>
        <xs:element name="TotalAmount"  type="xs:decimal" minOccurs="0"/>
        <xs:element name="Items" minOccurs="0" maxOccurs="unbounded">
          <xs:complexType>
            <xs:sequence>
              <xs:element name="Material"  type="xs:string"  minOccurs="0"/>
              <xs:element name="Quantity"  type="xs:integer" minOccurs="0"/>
              <xs:element name="UnitPrice" type="xs:decimal" minOccurs="0"/>
            </xs:sequence>
          </xs:complexType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
```

### XSD Rules — NEVER do these:
- `targetNamespace` attribute — breaks CPI path resolution
- `xmlns:tns` prefix references
- `elementFormDefault="qualified"` with targetNamespace
- Deep nesting (more than 4 levels)

### XSD Design Guidelines
- Root element: singular noun, CamelCase (Product, Order, Material, Delivery)
- Field names: CamelCase for OData-style (MaterialNumber, OrderDate)
- Field names: UPPER_CASE for IDoc-style (MATNR, WERKS, BUDAT)
- Use `minOccurs="0"` on most elements
- Use `maxOccurs="unbounded"` for repeating elements (line items)
- Types: xs:string for most, xs:decimal for amounts, xs:integer for quantities

---

## PART 6: GENERATION RULES (AI MUST FOLLOW)

1. For SUM/TOTAL of repeating values — use `sum((/path/to/repeating/field))` — NOT Groovy
2. For COUNT of occurrences — use `count()`
3. For repeating 1 source value to N targets — use `useOneAsMany()`
4. Never add targetNamespace to XSDs
5. Context determines which function to use — always check source/target cardinality
6. Statistics functions (sum/average/count) collapse N→1 automatically
7. `useOneAsMany` expands 1→N automatically
8. Direct copy when source and target have same cardinality and context
9. Root element name in lnk MUST exactly match the xs:element name in the XSD
10. All paths must start with /RootElementName/ matching the XSD
11. Use real fname values: TransformDate not formatDate, Equals not equals, SplitByValue not splitbyvalue
12. Separators in concat go in delimeter binding — not as a third arg brick
13. Date functions need calend binding along with iform/oform
14. Map container elements (parent nodes) as well as leaf fields for proper structure

---

## PART 7: COMMON INTEGRATION PATTERNS

### IDoc → OData Field Mappings
| IDoc Field | OData Field | Rule |
|-----------|-------------|------|
| MATNR | MaterialNumber | direct |
| MEINS | BaseUnit | toUpperCase |
| MAKTX | ProductDescription | direct |
| ERSDA | CreationDate | formatDate(yyyyMMdd, yyyy-MM-dd) |
| MTART | MaterialType | direct |
| WERKS | Plant | direct |
| LGORT | StorageLocation | direct |
| BUKRS | CompanyCode | direct |
| KOSTL | CostCenter | direct |
| BWART | MovementType | direct |
| MENGE | Quantity | direct |

### Date Format Tokens
| Token | Meaning | Example |
|-------|---------|---------|
| yyyyMMdd | Date, no separators | 20240101 |
| yyyy-MM-dd | ISO date | 2024-01-01 |
| dd.MM.yyyy | German format | 01.01.2024 |
| HHmmss | Time, no separators | 143022 |
| HH:mm:ss | Time with colons | 14:30:22 |
| yyyyMMddHHmmss | DateTime combined | 20240101143022 |

### Concat Patterns
| Goal | Expression |
|------|-----------|
| Date + T + Time | (/date)+T+(/time) |
| Plant + _ + Location | (/Plant)+_+(/Location) |
| First + Space + Last | (/FirstName)+ +(/LastName) |
| CompCode + - + CostCenter | (/CompCode)+-+(/CostCenter) |

---

## 5. ALL NODE FUNCTIONS — CORRECT fname VALUES

### STRING FUNCTIONS
| User writes | fname in XML | Bindings |
|-------------|--------------|---------|
| toUpperCase((/field)) | toUpperCase | none |
| toLowerCase((/field)) | toLowerCase | none |
| trim((/field)) | trim | none |
| length((/field)) | length | none |
| substring((/f), 0, 5) | substring | from=0, to=5 |
| (/f1)+SEP+(/f2) | concat | delimeter=SEP |
| replaceAll((/f), old, new) | replaceString | search=old, replace=new |
| SplitByValue((/f), ,) | SplitByValue | delimeter=, |
| indexOf((/f), text) | indexOf | search=text |
| lastIndexOf((/f), text) | lastIndexOf | search=text |
| endsWith((/f), suffix) | endsWith | value=suffix |
| startsWith((/f), prefix) | startsWith | value=prefix |
| equalsS((/f), val) | equalsS | (second arg) |
| compare((/f1), (/f2)) | compare | (two args) |
| contains((/f), text) | contains | search=text |
| copyValue((/f)) | copyValue | none |

### DATE FUNCTIONS
| User writes | fname in XML | Bindings |
|-------------|--------------|---------|
| formatDate((/f), yyyyMMdd, yyyy-MM-dd) | **TransformDate** | iform=yyyyMMdd, oform=yyyy-MM-dd, calend=... |
| currentDate() | currentDate | none (no source arg) |
| DateBefore((/d1), (/d2)) | DateBefore | (two args) |
| DateAfter((/d1), (/d2)) | DateAfter | (two args) |

**IMPORTANT:** `formatDate` is a user alias — real fname is `TransformDate`

### ARITHMETIC
| User writes | fname | Note |
|-------------|-------|------|
| add((/f1), (/f2)) | add | two source args |
| subtract((/f1), (/f2)) | subtract | |
| multiply((/f1), (/f2)) | multiply | |
| divide((/f1), (/f2)) | divide | |
| abs((/f)) | abs | single arg |
| neg((/f)) | neg | single arg |
| inv((/f)) | inv | single arg — 1/x |
| sqrt((/f)) | sqrt | single arg |
| sqr((/f)) | sqr | single arg |
| round((/f)) | round | single arg |
| ceil((/f)) | ceil | single arg |
| floor((/f)) | floor | single arg |
| max((/f1), (/f2)) | max | two args |
| min((/f1), (/f2)) | min | two args |
| FormatNum((/f), 0.00) | FormatNum | format=0.00 |

### BOOLEAN / CONDITIONAL
| User writes | fname | Note |
|-------------|-------|------|
| if((/cond), yes, no) | if | three args |
| ifS((/f), val, yes, no) | ifS | four args |
| ifWithoutElse((/c), val) | ifWithoutElse | |
| ifSWithoutElse((/f), val, yes) | ifSWithoutElse | |
| equals((/f), VALUE) | **Equals** | capital E |
| notEquals((/f), VALUE) | notEquals | |
| isNil((/f)) | isNil | single arg |
| Not((/bool)) | Not | single arg |
| And((/b1), (/b2)) | And | two args |
| Or((/b1), (/b2)) | Or | two args |

**IMPORTANT:** `equals` — real fname is `Equals` (capital E)

### STATISTICS FUNCTIONS — USE THESE FOR AGGREGATION (no Groovy needed!)
| User writes | fname | What it does |
|-------------|-------|-------------|
| sum((/f)) | sum | **SUM of ALL occurrences** — e.g. sum all Item/Quantity → TotalQuantity |
| average((/f)) | average | Average of all values in queue |
| count((/f)) | count | Count of occurrences |
| index((/f)) | index | 0-based index of current occurrence |
| first((/f)) | first | First value in the queue |
| last((/f)) | last | Last value in the queue |

**CONTEXT RULES for Statistics:**
- Statistics functions work on ALL values of a REPEATING source field (maxOccurs="unbounded")
- `sum((/Order/Items/Item/Quantity))` takes every Quantity occurrence and returns their SUM
- No Groovy UDF needed — this is the standard CPI way to aggregate
- Statistics collapse context automatically — result is ONE value per source context

### NODE / CONTEXT FUNCTIONS
| User writes | fname | Note |
|-------------|-------|------|
| useOneAsMany((/f)) | useOneAsMany | repeat one value for N target occurrences |
| SplitByValue((/f), ,) | **SplitByValue** | capital S, delimeter binding |
| mapWithDefault((/f), val) | mapWithDefault | default_value binding |
| exists((/f)) | exists | boolean result |
| getHeader(NAME) | getHeader | headerName binding |
| getProperty(NAME) | getProperty | propName binding |
| removeContexts((/f)) | removeContexts | flatten hierarchy to list |
| collapseContexts((/f)) | collapseContexts | merge N contexts into 1 |
| createIf((/cond)) | createIf | |
| sort((/f)) | sort | order=ascending |
| sortByKey((/f)) | sortByKey | |

**IMPORTANT:** `splitByValue` user alias — real fname is `SplitByValue` (capital S)

---

## 6. PATH FORMAT RULES

- Paths start with `/RootElement/Parent/Child`
- Root element = the `name` attribute of the top-level `xs:element` in XSD
- NO namespace prefixes in paths, even for namespaced XSDs
- Only leaf fields (no children) should be mapped as Src/Dst fields
- Container elements can be mapped for structure linking (useOneAsMany etc.)

### Example paths
```
Source XSD root "msg":    /msg/header/date, /msg/body/stockreport/ln/mn
Target XSD root "Header": /Header/HeaderType/RunDate
IDoc MATMAS05:            /MATMAS05/IDOC/E1MARAM/MATNR
OData A_Product:          /A_Product/Product/MaterialNumber
```

---

## 7. COMMON INTEGRATION PATTERNS

### Concat Patterns
| Goal | Expression |
|------|-----------|
| Date + T + Time | (/date)+T+(/time) |
| Plant + _ + Location | (/Plant)+_+(/Location) |
| First + Space + Last | (/FirstName)+ +(/LastName) |
| CompCode + - + CostCenter | (/CompCode)+-+(/CostCenter) |

---

## 8. SAP CPI VERSION & API INFO

- CPI API version: OData v2, path: /api/v1/
- Message Mapping artifact: MessageMappingDesigntimeArtifacts
- iFlow artifact: IntegrationDesigntimeArtifacts
- Value Mapping: ValueMappingDesigntimeArtifacts
- Script Collection: ScriptCollectionDesigntimeArtifacts
- Deploy: DeployMessageMappingDesigntimeArtifact?Id='ID'&Version='active'
- .mmap namespace: urn:sap-com:xi
- XiTrafo namespace: urn:sap-com:xi:mapping:xitrafo
- Mapping tool version: XI7.1 (use this in generated mmaps)
