"""Realistic coding tasks. Each has a prompt, hidden tests, and a reference answer proving the test is fair."""

CPP_LRU_PROMPT = """Write a thread-safe LRU cache in C++17 as a single header.
template <typename K, typename V> class LRUCache with:
- explicit LRUCache(std::size_t capacity)
- std::optional<V> get(const K& key): a hit counts as a use
- void put(const K& key, const V& value): updates an existing key and counts as a use; when full, evicts the least recently used key
- std::size_t size() const
Use only the standard library. Do not write main(). Return only one C++ code block."""

CPP_LRU_TEST = r"""
#include <cassert>
#include <cstdio>
#include <string>
#include <thread>
#include <vector>
int main() {
    { LRUCache<int, std::string> c(2); c.put(1, "a"); c.put(2, "b"); assert(c.get(1).value() == "a");
      c.put(3, "c"); assert(!c.get(2).has_value()); assert(c.get(1).value() == "a"); assert(c.get(3).value() == "c"); assert(c.size() == 2); }
    { LRUCache<int, int> c(2); c.put(1, 1); c.put(2, 2); c.put(1, 10); c.put(3, 3);
      assert(!c.get(2).has_value()); assert(c.get(1).value() == 10); assert(c.size() == 2); }
    { LRUCache<int, int> c(1); c.put(1, 1); c.put(2, 2); assert(!c.get(1).has_value()); assert(c.get(2).value() == 2); assert(c.size() == 1); }
    { LRUCache<int, int> c(8); std::vector<std::thread> ts;
      for (int t = 0; t < 4; ++t) ts.emplace_back([&c, t] { for (int i = 0; i < 3000; ++i) { c.put(t * 100000 + i % 20, i); c.get(i % 20); } });
      for (auto& t : ts) t.join();
      assert(c.size() <= 8); }
    puts("OK");
}
"""

CPP_LRU_REF = r"""
#include <cstddef>
#include <list>
#include <mutex>
#include <optional>
#include <unordered_map>
#include <utility>
template <typename K, typename V>
class LRUCache {
    std::size_t cap_;
    std::list<std::pair<K, V>> items_;
    std::unordered_map<K, typename std::list<std::pair<K, V>>::iterator> index_;
    mutable std::mutex mu_;
public:
    explicit LRUCache(std::size_t capacity) : cap_(capacity) {}
    std::optional<V> get(const K& key) {
        std::lock_guard<std::mutex> lock(mu_);
        auto it = index_.find(key);
        if (it == index_.end()) return std::nullopt;
        items_.splice(items_.begin(), items_, it->second);
        return it->second->second;
    }
    void put(const K& key, const V& value) {
        std::lock_guard<std::mutex> lock(mu_);
        auto it = index_.find(key);
        if (it != index_.end()) {
            it->second->second = value;
            items_.splice(items_.begin(), items_, it->second);
            return;
        }
        if (cap_ == 0) return;
        if (items_.size() == cap_) { index_.erase(items_.back().first); items_.pop_back(); }
        items_.emplace_front(key, value);
        index_[key] = items_.begin();
    }
    std::size_t size() const { std::lock_guard<std::mutex> lock(mu_); return items_.size(); }
};
"""

CPP_MATRIX_PROMPT = """Write a C++17 class Matrix that stores doubles in a manually allocated array (new[] and delete[]; no std::vector and no smart pointers).
- Matrix(int rows, int cols): zero-filled; throws std::invalid_argument if rows <= 0 or cols <= 0
- destructor, copy constructor, copy assignment, move constructor, move assignment
- double& at(int r, int c) and double at(int r, int c) const: throw std::out_of_range when out of bounds
- int rows() const and int cols() const
- Matrix operator+(const Matrix& o) const and Matrix operator*(const Matrix& o) const (matrix multiplication): throw std::invalid_argument on a size mismatch
- bool operator==(const Matrix& o) const
Do not write main(). Return only one C++ code block."""

CPP_MATRIX_TEST = r"""
#include <cassert>
#include <cstdio>
#include <stdexcept>
#include <utility>
template <class E, class F> bool throws(F f) { try { f(); } catch (const E&) { return true; } catch (...) {} return false; }
int main() {
    Matrix a(2, 3); assert(a.rows() == 2 && a.cols() == 3 && a.at(1, 2) == 0.0);
    for (int r = 0; r < 2; ++r) for (int c = 0; c < 3; ++c) a.at(r, c) = r * 3 + c + 1;
    Matrix b(3, 2); for (int r = 0; r < 3; ++r) for (int c = 0; c < 2; ++c) b.at(r, c) = r * 2 + c + 7;
    Matrix p = a * b; assert(p.rows() == 2 && p.cols() == 2);
    assert(p.at(0, 0) == 58 && p.at(0, 1) == 64 && p.at(1, 0) == 139 && p.at(1, 1) == 154);
    Matrix s = a + a; assert(s.at(1, 2) == 12);
    Matrix copy(a); copy.at(0, 0) = 99; assert(a.at(0, 0) == 1); assert(!(copy == a));
    Matrix asg(1, 1); asg = a; assert(asg == a); asg = *&asg; assert(asg == a);
    Matrix moved(std::move(copy)); assert(moved.at(0, 0) == 99);
    Matrix mv(1, 1); mv = std::move(moved); assert(mv.at(0, 0) == 99); assert(mv.rows() == 2);
    const Matrix& ca = a; assert(ca.at(1, 1) == 5);
    assert(throws<std::invalid_argument>([] { Matrix x(0, 2); }));
    assert(throws<std::invalid_argument>([] { Matrix x(2, -1); }));
    assert(throws<std::out_of_range>([&] { a.at(2, 0); }));
    assert(throws<std::out_of_range>([&] { ca.at(0, -1); }));
    assert(throws<std::invalid_argument>([&] { auto x = a * a; }));
    assert(throws<std::invalid_argument>([&] { auto x = a + b; }));
    assert(!(a == b));
    puts("OK");
}
"""

CPP_MATRIX_REF = r"""
#include <algorithm>
#include <stdexcept>
#include <utility>
class Matrix {
    int r_ = 0, c_ = 0; double* d_ = nullptr;
    void check(int r, int c) const { if (r < 0 || c < 0 || r >= r_ || c >= c_) throw std::out_of_range("index"); }
public:
    Matrix(int rows, int cols) : r_(rows), c_(cols) {
        if (rows <= 0 || cols <= 0) throw std::invalid_argument("size");
        d_ = new double[rows * cols]();
    }
    ~Matrix() { delete[] d_; }
    Matrix(const Matrix& o) : r_(o.r_), c_(o.c_), d_(new double[o.r_ * o.c_]) { std::copy(o.d_, o.d_ + r_ * c_, d_); }
    Matrix(Matrix&& o) noexcept : r_(o.r_), c_(o.c_), d_(o.d_) { o.d_ = nullptr; o.r_ = o.c_ = 0; }
    Matrix& operator=(Matrix o) noexcept { std::swap(r_, o.r_); std::swap(c_, o.c_); std::swap(d_, o.d_); return *this; }
    double& at(int r, int c) { check(r, c); return d_[r * c_ + c]; }
    double at(int r, int c) const { check(r, c); return d_[r * c_ + c]; }
    int rows() const { return r_; }
    int cols() const { return c_; }
    Matrix operator+(const Matrix& o) const {
        if (r_ != o.r_ || c_ != o.c_) throw std::invalid_argument("size");
        Matrix m(r_, c_); for (int i = 0; i < r_ * c_; ++i) m.d_[i] = d_[i] + o.d_[i]; return m;
    }
    Matrix operator*(const Matrix& o) const {
        if (c_ != o.r_) throw std::invalid_argument("size");
        Matrix m(r_, o.c_);
        for (int i = 0; i < r_; ++i) for (int j = 0; j < o.c_; ++j) for (int k = 0; k < c_; ++k) m.d_[i * o.c_ + j] += at(i, k) * o.at(k, j);
        return m;
    }
    bool operator==(const Matrix& o) const { return r_ == o.r_ && c_ == o.c_ && std::equal(d_, d_ + r_ * c_, o.d_); }
};
"""

CPP_BUGFIX_PROMPT = """This C++ singly linked list has several bugs: crashes, memory errors and wrong results. Find and fix all of them without changing the public interface. The class must not leak memory.

```cpp
#include <cstddef>
#include <stdexcept>
struct Node {
    int value;
    Node* next;
    Node(int v, Node* n = nullptr) : value(v), next(n) {}
};
class List {
    Node* head = nullptr;
public:
    List() = default;
    List(const List&) = delete;
    List& operator=(const List&) = delete;
    ~List() {
        while (head) {
            delete head;
            head = head->next;
        }
    }
    void push_back(int v) {
        Node* n = new Node(v);
        if (!head) head = n;
        Node* c = head;
        while (c->next) c = c->next;
        c->next = n;
    }
    void remove_all(int v) {
        Node* c = head;
        while (c && c->next) {
            if (c->next->value == v) {
                delete c->next;
                c->next = c->next->next;
            }
            c = c->next;
        }
    }
    void reverse() {
        Node* prev = nullptr;
        Node* c = head;
        while (c) {
            c->next = prev;
            prev = c;
            c = c->next;
        }
        head = prev;
    }
    std::size_t size() const {
        std::size_t n = 0;
        for (Node* c = head; c; c = c->next) ++n;
        return n;
    }
    int at(std::size_t i) const {
        Node* c = head;
        while (i--) c = c->next;
        return c->value;
    }
};
```

Return the complete fixed code in one C++ code block. Do not write main()."""

CPP_BUGFIX_TEST = r"""
#include <cassert>
#include <cstdio>
#include <stdexcept>
int main() {
    { List l; assert(l.size() == 0); l.reverse(); l.remove_all(1); assert(l.size() == 0); }
    { List l; l.push_back(1); assert(l.size() == 1 && l.at(0) == 1); }
    { List l; for (int v : {1, 2, 3}) l.push_back(v); l.reverse(); assert(l.at(0) == 3 && l.at(1) == 2 && l.at(2) == 1 && l.size() == 3); }
    { List l; for (int v : {7, 7, 1, 7, 7, 2, 7}) l.push_back(v); l.remove_all(7); assert(l.size() == 2 && l.at(0) == 1 && l.at(1) == 2); }
    { List l; for (int v : {5, 5, 5}) l.push_back(v); l.remove_all(5); assert(l.size() == 0); l.push_back(9); assert(l.at(0) == 9); }
    { List l; l.push_back(1); bool threw = false; try { l.at(1); } catch (const std::out_of_range&) { threw = true; } assert(threw); }
    puts("OK");
}
"""

CPP_BUGFIX_REF = r"""
#include <cstddef>
#include <stdexcept>
struct Node {
    int value;
    Node* next;
    Node(int v, Node* n = nullptr) : value(v), next(n) {}
};
class List {
    Node* head = nullptr;
public:
    List() = default;
    List(const List&) = delete;
    List& operator=(const List&) = delete;
    ~List() { while (head) { Node* n = head->next; delete head; head = n; } }
    void push_back(int v) {
        Node* n = new Node(v);
        if (!head) { head = n; return; }
        Node* c = head;
        while (c->next) c = c->next;
        c->next = n;
    }
    void remove_all(int v) {
        Node** p = &head;
        while (*p) {
            if ((*p)->value == v) { Node* d = *p; *p = d->next; delete d; }
            else p = &(*p)->next;
        }
    }
    void reverse() {
        Node* prev = nullptr; Node* c = head;
        while (c) { Node* n = c->next; c->next = prev; prev = c; c = n; }
        head = prev;
    }
    std::size_t size() const { std::size_t n = 0; for (Node* c = head; c; c = c->next) ++n; return n; }
    int at(std::size_t i) const {
        Node* c = head;
        while (c && i--) c = c->next;
        if (!c) throw std::out_of_range("index");
        return c->value;
    }
};
"""

PY_BUGFIX_PROMPT = '''These three Python functions have bugs. Each docstring describes the correct behaviour. Fix them.

```python
def paginate(items, page, per_page=10):
    """Return the items on a 1-indexed page. Raise ValueError if page < 1 or per_page < 1."""
    start = page * per_page
    return items[start:start + per_page]


def word_freq(text, stop=[]):
    """Return (word, count) pairs: case-insensitive, punctuation ignored, words in stop excluded,
    most common first, ties in alphabetical order."""
    counts = {}
    for w in text.split():
        if w not in stop:
            counts[w] = counts.get(w, 0) + 1
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)


def merge_config(base, override):
    """Return a deep merge of override onto base. Nested dicts merge; other values are replaced.
    Neither argument may be changed."""
    out = base
    for k, v in override.items():
        if isinstance(v, dict) and k in out:
            merge_config(out[k], v)
        else:
            out[k] = v
    return out
```

Return all three fixed functions in one Python code block, with no explanation.'''

PY_BUGFIX_TEST = r"""
from sol import paginate, word_freq, merge_config
import copy
assert paginate([1, 2, 3, 4, 5], 1, 2) == [1, 2]
assert paginate([1, 2, 3, 4, 5], 3, 2) == [5]
assert paginate([1], 2) == []
for a in [(0, 2), (1, 0), (-1, 2)]:
    try: paginate([1], *a)
    except ValueError: pass
    else: raise AssertionError(a)
assert word_freq("The cat. the DOG, a cat!", ["a"]) == [("cat", 2), ("the", 2), ("dog", 1)]
assert word_freq("B a") == [("a", 1), ("b", 1)]
assert word_freq("The the", stop=["the"]) == []
base = {"a": 1, "n": {"x": 1, "deep": {"p": 1}}}; over = {"a": 2, "n": {"y": 2, "deep": {"q": 2}}, "z": 3}
b0, o0 = copy.deepcopy(base), copy.deepcopy(over)
assert merge_config(base, over) == {"a": 2, "n": {"x": 1, "y": 2, "deep": {"p": 1, "q": 2}}, "z": 3}
assert base == b0 and over == o0
assert merge_config({"a": {"x": 1}}, {"a": 5}) == {"a": 5}
assert merge_config({"a": 5}, {"a": {"x": 1}}) == {"a": {"x": 1}}
print("OK")
"""

PY_BUGFIX_REF = r"""
import copy, re
def paginate(items, page, per_page=10):
    if page < 1 or per_page < 1:
        raise ValueError("bad page")
    start = (page - 1) * per_page
    return items[start:start + per_page]
def word_freq(text, stop=()):
    banned = {s.lower() for s in stop}
    counts = {}
    for w in re.findall(r"[a-z0-9']+", text.lower()):
        if w not in banned:
            counts[w] = counts.get(w, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
def merge_config(base, override):
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge_config(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out
"""

PY_TOPO_PROMPT = """Implement topo_sort(graph) in Python. graph maps each node (string) to its prerequisite nodes. Include nodes that appear only as prerequisites. Return prerequisites before dependents. Whenever multiple nodes are ready, choose the lexicographically smallest. Raise ValueError on any cycle. Do not mutate graph. Return only one Python code block, no explanation."""

PY_TOPO_TEST = r"""
from sol import topo_sort
import copy
assert topo_sort({'app':['lib'],'lib':['base']})==['base','lib','app']
assert topo_sort({'b':[],'a':[],'c':['a']})==['a','b','c']
assert topo_sort({})==[]
assert topo_sort({'a':['x','x']})==['x','a']
g={'b':['a'],'a':[]}; old=copy.deepcopy(g); topo_sort(g); assert g==old
for g in [{'a':['a']},{'a':['b'],'b':['a']},{'ok':[],'a':['b'],'b':['a']}]:
    try: topo_sort(g)
    except ValueError: pass
    else: raise AssertionError('cycle not detected')
print("OK")
"""

PY_TOPO_REF = r"""
import heapq
def topo_sort(graph):
    pending, dependents = {}, {}
    for node, prereqs in graph.items():
        pending.setdefault(node, set())
        for p in prereqs:
            pending[node].add(p); pending.setdefault(p, set()); dependents.setdefault(p, set()).add(node)
    ready = [n for n, s in pending.items() if not s]
    heapq.heapify(ready); out = []
    while ready:
        n = heapq.heappop(ready); out.append(n)
        for d in dependents.get(n, ()):
            pending[d].discard(n)
            if not pending[d]: heapq.heappush(ready, d)
    if len(out) != len(pending): raise ValueError("cycle")
    return out
"""

PY_CSV_PROMPT = """Write a Python function summarize_sales(path) using only the standard library.
The file is a CSV with the header date,region,product,qty,price. Fields may be quoted and may contain commas.
A row is invalid if qty or price is missing or not a number, or if qty <= 0 or price < 0. Skip invalid rows.
Return a dict with:
- "rows": number of valid rows
- "skipped": number of invalid rows
- "total": total revenue (qty * price), rounded to 2 decimals
- "by_region": dict of region to revenue, each rounded to 2 decimals
- "top_product": product with the highest revenue, ties broken alphabetically, or None if there are no valid rows
Return only one Python code block, no explanation."""

PY_CSV_TEST = r"""
from sol import summarize_sales
import os, tempfile
def run(text):
    fd, p = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", newline="") as f: f.write(text)
    return summarize_sales(p)
r = run('date,region,product,qty,price\n2026-01-01,North,"Widget, large",2,10.50\n2026-01-02,South,Gadget,1,5\n2026-01-03,North,Gadget,x,5\n2026-01-04,South,Widget,0,5\n2026-01-05,,Gadget,3,\n2026-01-06,West,Bolt,4,-1\n2026-01-07,South,Gadget,3,5\n')
assert r["rows"] == 3 and r["skipped"] == 4, r
assert r["total"] == 41.0, r
assert r["by_region"] == {"North": 21.0, "South": 20.0}, r
assert r["top_product"] == "Widget, large", r
e = run("date,region,product,qty,price\n")
assert e["rows"] == 0 and e["skipped"] == 0 and e["total"] == 0 and e["by_region"] == {} and e["top_product"] is None, e
t = run("date,region,product,qty,price\n1,A,zeta,1,2\n2,A,alpha,2,1\n")
assert t["top_product"] == "alpha", t
print("OK")
"""

PY_CSV_REF = r"""
import csv
def summarize_sales(path):
    rows = skipped = 0
    total = 0.0
    regions, products = {}, {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                q, p = float(row["qty"]), float(row["price"])
            except (TypeError, ValueError):
                skipped += 1; continue
            if q <= 0 or p < 0:
                skipped += 1; continue
            rev = q * p; rows += 1; total += rev
            regions[row["region"]] = regions.get(row["region"], 0.0) + rev
            products[row["product"]] = products.get(row["product"], 0.0) + rev
    top = min(products, key=lambda k: (-products[k], k)) if products else None
    return {"rows": rows, "skipped": skipped, "total": round(total, 2),
            "by_region": {k: round(v, 2) for k, v in regions.items()}, "top_product": top}
"""

JAVA_PROMPT = """Write a single Java 17 source file Library.java with no package statement. It has one public class Library, and any helper classes must be nested inside it.
- void addBook(String isbn, String title): IllegalArgumentException if the isbn already exists
- void borrow(String isbn, String member, java.time.LocalDate date): NoSuchElementException if the isbn is unknown, IllegalStateException if already borrowed
- void giveBack(String isbn): NoSuchElementException if unknown, IllegalStateException if not borrowed
- java.util.List<String> overdue(java.time.LocalDate today, int days): titles of books currently borrowed for strictly more than days days, sorted alphabetically
- java.util.Map<String, Integer> loansByMember(): current number of borrowed books per member, omitting members with none
Return only one Java code block."""

JAVA_TEST = r"""
import java.time.LocalDate;
import java.util.*;
public class Test {
    static boolean throwsEx(Class<?> c, Runnable r) { try { r.run(); } catch (Exception e) { return c.isInstance(e); } return false; }
    static void ok(boolean b, String m) { if (!b) throw new AssertionError(m); }
    public static void main(String[] a) {
        Library l = new Library();
        l.addBook("1", "Zebra"); l.addBook("2", "Apple"); l.addBook("3", "Mango");
        ok(throwsEx(IllegalArgumentException.class, () -> l.addBook("1", "Dup")), "dup");
        LocalDate d = LocalDate.of(2026, 1, 1);
        l.borrow("1", "ana", d); l.borrow("2", "ana", d.plusDays(5));
        ok(throwsEx(IllegalStateException.class, () -> l.borrow("1", "bob", d)), "double borrow");
        ok(throwsEx(NoSuchElementException.class, () -> l.borrow("9", "bob", d)), "unknown borrow");
        ok(throwsEx(IllegalStateException.class, () -> l.giveBack("3")), "not borrowed");
        ok(throwsEx(NoSuchElementException.class, () -> l.giveBack("9")), "unknown return");
        ok(l.overdue(d.plusDays(10), 10).isEmpty(), "strictly more");
        ok(l.overdue(d.plusDays(11), 10).equals(List.of("Zebra")), "one overdue");
        ok(l.overdue(d.plusDays(30), 10).equals(List.of("Apple", "Zebra")), "sorted");
        ok(l.loansByMember().equals(Map.of("ana", 2)), "loans");
        l.giveBack("1"); l.giveBack("2");
        ok(l.loansByMember().isEmpty(), "no empty members");
        ok(l.overdue(d.plusDays(30), 10).isEmpty(), "returned");
        l.borrow("1", "bob", d);
        ok(l.loansByMember().equals(Map.of("bob", 1)), "reborrow");
        System.out.println("OK");
    }
}
"""

JAVA_REF = r"""
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.*;
public class Library {
    private static class Book { String title, member; LocalDate date; Book(String t) { title = t; } }
    private final Map<String, Book> books = new HashMap<>();
    private Book get(String isbn) { Book b = books.get(isbn); if (b == null) throw new NoSuchElementException(isbn); return b; }
    public void addBook(String isbn, String title) { if (books.containsKey(isbn)) throw new IllegalArgumentException(isbn); books.put(isbn, new Book(title)); }
    public void borrow(String isbn, String member, LocalDate date) { Book b = get(isbn); if (b.member != null) throw new IllegalStateException(isbn); b.member = member; b.date = date; }
    public void giveBack(String isbn) { Book b = get(isbn); if (b.member == null) throw new IllegalStateException(isbn); b.member = null; b.date = null; }
    public List<String> overdue(LocalDate today, int days) {
        List<String> out = new ArrayList<>();
        for (Book b : books.values()) if (b.member != null && ChronoUnit.DAYS.between(b.date, today) > days) out.add(b.title);
        Collections.sort(out); return out;
    }
    public Map<String, Integer> loansByMember() {
        Map<String, Integer> m = new HashMap<>();
        for (Book b : books.values()) if (b.member != null) m.merge(b.member, 1, Integer::sum);
        return m;
    }
}
"""

SQL_PROMPT = """SQLite schema:
students(id INTEGER PRIMARY KEY, name TEXT)
courses(id INTEGER PRIMARY KEY, title TEXT)
grades(student_id INTEGER, course_id INTEGER, grade REAL)

Write one SQL query that returns, for each course with at least 3 graded students, these columns in this order: title, n (number of grades), avg_grade (average rounded to 2 decimals), passed (number of grades >= 5).
Courses with no grades must not appear. Order by avg_grade descending, then title ascending.
Return only one SQL code block."""

SQL_TEST = r"""
import sqlite3
q = open("sol.sql").read().strip().rstrip(";")
db = sqlite3.connect(":memory:")
db.executescript('''
create table students(id integer primary key, name text);
create table courses(id integer primary key, title text);
create table grades(student_id integer, course_id integer, grade real);
insert into courses values (1,'Algebra'),(2,'Biology'),(3,'Chemistry'),(4,'Databases'),(5,'Empty');
insert into students values (1,'a'),(2,'b'),(3,'c'),(4,'d');
insert into grades values (1,1,10),(2,1,5),(3,1,4),(1,2,8),(2,2,7),(3,2,4),(1,3,9),(2,3,10),(1,4,5),(2,4,6),(3,4,8),(4,4,0.0);
''')
rows = [tuple(r) for r in db.execute(q)]
assert rows == [("Algebra", 3, 6.33, 2), ("Biology", 3, 6.33, 2), ("Databases", 4, 4.75, 3)], rows
print("OK")
"""

SQL_REF = """
SELECT c.title, COUNT(*) AS n, ROUND(AVG(g.grade), 2) AS avg_grade,
       SUM(CASE WHEN g.grade >= 5 THEN 1 ELSE 0 END) AS passed
FROM courses c JOIN grades g ON g.course_id = c.id
GROUP BY c.id, c.title HAVING COUNT(*) >= 3
ORDER BY avg_grade DESC, c.title ASC;
"""

JS_PROMPT = """Write a Node.js CommonJS module exporting an async function retry(fn, options).
- options is optional and may contain attempts (default 3), baseMs (default 100), and shouldRetry (default: always true)
- call await fn(attempt), where attempt starts at 1, and return its result on success
- after a failure, if shouldRetry(error) is false or attempts are used up, rethrow that error immediately
- otherwise wait baseMs * 2 ** (attempt - 1) milliseconds before the next attempt
End with module.exports = { retry };. Use no external packages. Return only one JavaScript code block."""

JS_TEST = r"""
const assert = require('assert');
const { retry } = require('./sol.js');
(async () => {
  assert.strictEqual(await retry(async () => 5), 5);
  let calls = [];
  const v = await retry(async (n) => { calls.push(n); if (n < 3) throw new Error('x'); return 'ok'; }, { baseMs: 20 });
  assert.strictEqual(v, 'ok'); assert.deepStrictEqual(calls, [1, 2, 3]);
  const t = Date.now(); let n = 0;
  await assert.rejects(retry(async () => { n++; throw new Error('last'); }, { attempts: 3, baseMs: 50 }), /last/);
  assert.strictEqual(n, 3);
  const dt = Date.now() - t; assert(dt >= 140 && dt < 400, 'delay ' + dt);
  n = 0;
  await assert.rejects(retry(async () => { n++; throw new Error('fatal'); }, { attempts: 5, baseMs: 10, shouldRetry: () => false }), /fatal/);
  assert.strictEqual(n, 1);
  const t2 = Date.now(); n = 0;
  await assert.rejects(retry(async () => { n++; throw new Error('one'); }, { attempts: 1, baseMs: 500 }), /one/);
  assert.strictEqual(n, 1); assert(Date.now() - t2 < 200, 'no wait after final attempt');
  n = 0;
  assert.strictEqual(await retry(() => { n++; if (n < 2) throw new Error('sync'); return 7; }, { baseMs: 5 }), 7);
  console.log('OK');
})().catch((e) => { console.error(e); process.exit(1); });
"""

JS_REF = r"""
async function retry(fn, options = {}) {
  const { attempts = 3, baseMs = 100, shouldRetry = () => true } = options;
  for (let attempt = 1; ; attempt++) {
    try {
      return await fn(attempt);
    } catch (err) {
      if (attempt >= attempts || !shouldRetry(err)) throw err;
      await new Promise((r) => setTimeout(r, baseMs * 2 ** (attempt - 1)));
    }
  }
}
module.exports = { retry };
"""

TASKS = [
    dict(id='cpp_lru', lang='cpp', prompt=CPP_LRU_PROMPT, test=CPP_LRU_TEST, ref=CPP_LRU_REF, tsan=True),
    dict(id='cpp_matrix', lang='cpp', prompt=CPP_MATRIX_PROMPT, test=CPP_MATRIX_TEST, ref=CPP_MATRIX_REF),
    dict(id='cpp_bugfix', lang='cpp', prompt=CPP_BUGFIX_PROMPT, test=CPP_BUGFIX_TEST, ref=CPP_BUGFIX_REF),
    dict(id='py_bugfix', lang='py', prompt=PY_BUGFIX_PROMPT, test=PY_BUGFIX_TEST, ref=PY_BUGFIX_REF),
    dict(id='py_topo', lang='py', prompt=PY_TOPO_PROMPT, test=PY_TOPO_TEST, ref=PY_TOPO_REF),
    dict(id='py_csv', lang='py', prompt=PY_CSV_PROMPT, test=PY_CSV_TEST, ref=PY_CSV_REF),
    dict(id='java_library', lang='java', prompt=JAVA_PROMPT, test=JAVA_TEST, ref=JAVA_REF),
    dict(id='sql_report', lang='sql', prompt=SQL_PROMPT, test=SQL_TEST, ref=SQL_REF),
    dict(id='js_retry', lang='js', prompt=JS_PROMPT, test=JS_TEST, ref=JS_REF),
]
