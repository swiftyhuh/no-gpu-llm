"""Unseen tasks in the style of university coursework: operating systems (C), logic programming (Prolog), Java streams, C++ OOP."""

C_PIPE_PROMPT = """Write this C function for Linux. Do not write main().

int sum_in_child(const int *values, int n, long *result);

It must create a pipe, then fork. The child adds up the n values, writes the sum to the pipe and exits with status 0. The parent reads the sum into *result, closes its pipe ends, waits for the child, and returns 0.
Return -1 if pipe or fork fails, if the child does not exit with status 0, or if the parent cannot read a complete long. No zombie process may remain. Include the headers you need. Return only one C code block."""

C_PIPE_TEST = r"""
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>
int main(void) {
    int a[] = {1, 2, 3, 4, 5}; long r = -1;
    assert(sum_in_child(a, 5, &r) == 0 && r == 15);
    assert(waitpid(-1, NULL, WNOHANG) == -1 && errno == ECHILD);
    r = -1; assert(sum_in_child(a, 0, &r) == 0 && r == 0);
    int neg[] = {-10, 4}; assert(sum_in_child(neg, 2, &r) == 0 && r == -6);
    int big[] = {2000000000, 2000000000}; assert(sum_in_child(big, 2, &r) == 0 && r == 4000000000L);
    for (int i = 0; i < 50; ++i) assert(sum_in_child(a, 5, &r) == 0);
    assert(lseek(3, 0, SEEK_CUR) == -1 && errno == EBADF);
    puts("OK");
    return 0;
}
"""

C_PIPE_REF = r"""
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
int sum_in_child(const int *values, int n, long *result) {
    int fd[2];
    if (pipe(fd) == -1) return -1;
    pid_t pid = fork();
    if (pid == -1) { close(fd[0]); close(fd[1]); return -1; }
    if (pid == 0) {
        close(fd[0]);
        long s = 0;
        for (int i = 0; i < n; i++) s += values[i];
        ssize_t w = write(fd[1], &s, sizeof s);
        close(fd[1]);
        _exit(w == (ssize_t)sizeof s ? 0 : 1);
    }
    close(fd[1]);
    long v;
    ssize_t r = read(fd[0], &v, sizeof v);
    close(fd[0]);
    int st;
    if (waitpid(pid, &st, 0) == -1) return -1;
    if (r != (ssize_t)sizeof v || !WIFEXITED(st) || WEXITSTATUS(st) != 0) return -1;
    *result = v;
    return 0;
}
"""

PROLOG_PROMPT = """Write these SWI-Prolog predicates without using library predicates such as list_to_set, subtract, sumlist, nth0 or nth1.

remove_dups(+List, -Result): Result keeps the first occurrence of each element, in order.
insert_sorted(+X, +Sorted, -Result): inserts X into an ascending list, keeping it ascending.
subset_sum(+List, +Sum, -Subset): on backtracking, gives every sublist of List (keeping order) whose elements add up to Sum.

Return only one Prolog code block."""

PROLOG_TEST = r"""
:- initialization(main).
t(G) :- ( once(G) -> true ; format("FAILED: ~q~n", [G]), halt(1) ).
main :-
    t(remove_dups([1,2,1,3,2,4], [1,2,3,4])),
    t(remove_dups([], [])),
    t(remove_dups([a,a,a], [a])),
    t(insert_sorted(3, [1,2,4,5], [1,2,3,4,5])),
    t(insert_sorted(1, [], [1])),
    t(insert_sorted(9, [1,2], [1,2,9])),
    t(insert_sorted(0, [1,2], [0,1,2])),
    findall(S, subset_sum([1,2,3,4], 5, S), L),
    msort(L, M), t(M == [[1,4],[2,3]]),
    findall(S, subset_sum([1,2], 9, S), []),
    findall(S, subset_sum([], 0, S), E), t(E == [[]]),
    findall(R, remove_dups([1,1], R), Rs), t(Rs == [[1]]),
    writeln('OK'), halt(0).
"""

PROLOG_REF = r"""
member_(X, [X|_]).
member_(X, [_|T]) :- member_(X, T).
remove_dups(L, R) :- rd(L, [], R).
rd([], _, []).
rd([H|T], Seen, R) :- member_(H, Seen), !, rd(T, Seen, R).
rd([H|T], Seen, [H|R]) :- rd(T, [H|Seen], R).
insert_sorted(X, [], [X]).
insert_sorted(X, [H|T], [X,H|T]) :- X =< H, !.
insert_sorted(X, [H|T], [H|R]) :- insert_sorted(X, T, R).
subset_sum([], 0, []).
subset_sum([H|T], S, [H|R]) :- S1 is S - H, subset_sum(T, S1, R).
subset_sum([_|T], S, R) :- subset_sum(T, S, R).
"""

JAVA_PROMPT = """Write a single Java 17 file Report.java with no package statement. It has one public class Report, and helpers must be nested inside it.
- public record Student(String name, String group, java.util.List<Integer> grades)
- static java.util.Map<String, Double> averageByGroup(java.util.List<Student> students): the mean of each student's own mean, per group, skipping students with no grades; omit groups left with nobody
- static java.util.List<String> topStudents(java.util.List<Student> students, int n): names of the n students with the highest mean, ties in alphabetical order; students with no grades are ignored
- static java.util.Optional<Student> best(java.util.List<Student> students, String group): highest mean in that group, empty if none
Use the Streams API. Return only one Java code block."""

JAVA_TEST = r"""
import java.util.*;
public class Test {
    static void ok(boolean b, String m) { if (!b) throw new AssertionError(m); }
    public static void main(String[] a) {
        var s = List.of(new Report.Student("Ana", "A", List.of(10, 8)), new Report.Student("Bob", "A", List.of(6)),
                        new Report.Student("Cid", "B", List.of(9, 9, 9)), new Report.Student("Dan", "B", List.of()),
                        new Report.Student("Eve", "C", List.of()), new Report.Student("Aby", "C", List.of(9)));
        Map<String, Double> m = Report.averageByGroup(s);
        ok(Math.abs(m.get("A") - 7.5) < 1e-9, "A"); ok(Math.abs(m.get("B") - 9.0) < 1e-9, "B"); ok(m.size() == 3, "groups");
        ok(Report.topStudents(s, 3).equals(List.of("Aby", "Ana", "Cid")), "top " + Report.topStudents(s, 3));
        ok(Report.topStudents(s, 99).size() == 4, "no grades ignored");
        ok(Report.best(s, "B").get().name().equals("Cid"), "best");
        ok(Report.best(s, "Z").isEmpty(), "missing group");
        ok(Report.best(List.of(new Report.Student("X", "Q", List.of())), "Q").isEmpty(), "no grades");
        ok(Report.averageByGroup(List.of(new Report.Student("X", "Q", List.of()))).isEmpty(), "empty group");
        System.out.println("OK");
    }
}
"""

JAVA_REF = r"""
import java.util.*;
import java.util.stream.*;
public class Report {
    public record Student(String name, String group, List<Integer> grades) {
        double mean() { return grades.stream().mapToInt(Integer::intValue).average().orElse(0); }
    }
    static Map<String, Double> averageByGroup(List<Student> students) {
        return students.stream().filter(s -> !s.grades().isEmpty())
            .collect(Collectors.groupingBy(Student::group, Collectors.averagingDouble(Student::mean)));
    }
    static List<String> topStudents(List<Student> students, int n) {
        return students.stream().filter(s -> !s.grades().isEmpty())
            .sorted(Comparator.comparingDouble(Student::mean).reversed().thenComparing(Student::name))
            .limit(n).map(Student::name).toList();
    }
    static Optional<Student> best(List<Student> students, String group) {
        return students.stream().filter(s -> s.group().equals(group) && !s.grades().isEmpty())
            .max(Comparator.comparingDouble(Student::mean));
    }
}
"""

CPP_OOP_PROMPT = """Write this C++17 class design in one header, with no main().
- Abstract class Shape: virtual destructor, pure virtual double area() const, pure virtual std::string name() const, pure virtual std::unique_ptr<Shape> clone() const
- Circle(double r) and Rect(double w, double h) derive from Shape. Their constructors throw std::invalid_argument for values <= 0. name() returns "circle" and "rect". Use 3.14159265358979 for pi.
- Class Scene owns shapes in a std::vector<std::unique_ptr<Shape>>:
  - void add(std::unique_ptr<Shape> s): throws std::invalid_argument on nullptr
  - std::size_t size() const
  - double total_area() const
  - std::string largest() const: name of the largest shape, throws std::runtime_error if empty
  - a copy constructor and copy assignment that deep-copy the shapes
- std::ostream& operator<<(std::ostream&, const Scene&): writes each shape as name:area with two decimals, sorted by area ascending, separated by single spaces, with no trailing space. Printing must not reorder the Scene.
Return only one C++ code block."""

CPP_OOP_TEST = r"""
#include <cassert>
#include <cstdio>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <type_traits>
template <class E, class F> bool throws(F f) { try { f(); } catch (const E&) { return true; } catch (...) {} return false; }
int main() {
    static_assert(std::has_virtual_destructor<Shape>::value, "virtual dtor");
    static_assert(std::is_abstract<Shape>::value, "abstract");
    Scene s; assert(s.size() == 0 && s.total_area() == 0.0);
    assert(throws<std::runtime_error>([&] { s.largest(); }));
    assert(throws<std::invalid_argument>([&] { s.add(nullptr); }));
    assert(throws<std::invalid_argument>([] { Circle c(0); }));
    assert(throws<std::invalid_argument>([] { Rect r(1, -2); }));
    s.add(std::make_unique<Rect>(2, 3)); s.add(std::make_unique<Circle>(1));
    assert(s.size() == 2 && s.largest() == "rect");
    std::ostringstream o; o << s; assert(o.str() == "circle:3.14 rect:6.00");
    Scene c(s); c.add(std::make_unique<Rect>(10, 10)); assert(s.size() == 2 && c.size() == 3 && c.largest() == "rect");
    Scene d; d = c; d = *&d; assert(d.size() == 3);
    d = s; assert(d.size() == 2);
    std::ostringstream o2; o2 << d; assert(o2.str() == o.str());
    std::unique_ptr<Shape> p = std::make_unique<Circle>(2); auto q = p->clone(); assert(q->name() == "circle" && q->area() == p->area());
    puts("OK");
}
"""

CPP_OOP_REF = r"""
#include <algorithm>
#include <cstddef>
#include <iomanip>
#include <memory>
#include <ostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
class Shape {
public:
    virtual ~Shape() = default;
    virtual double area() const = 0;
    virtual std::string name() const = 0;
    virtual std::unique_ptr<Shape> clone() const = 0;
};
class Circle : public Shape {
    double r_;
public:
    explicit Circle(double r) : r_(r) { if (r <= 0) throw std::invalid_argument("r"); }
    double area() const override { return 3.14159265358979 * r_ * r_; }
    std::string name() const override { return "circle"; }
    std::unique_ptr<Shape> clone() const override { return std::make_unique<Circle>(*this); }
};
class Rect : public Shape {
    double w_, h_;
public:
    Rect(double w, double h) : w_(w), h_(h) { if (w <= 0 || h <= 0) throw std::invalid_argument("side"); }
    double area() const override { return w_ * h_; }
    std::string name() const override { return "rect"; }
    std::unique_ptr<Shape> clone() const override { return std::make_unique<Rect>(*this); }
};
class Scene {
    std::vector<std::unique_ptr<Shape>> shapes_;
public:
    Scene() = default;
    Scene(const Scene& o) { for (const auto& s : o.shapes_) shapes_.push_back(s->clone()); }
    Scene& operator=(const Scene& o) {
        if (this != &o) { Scene t(o); shapes_.swap(t.shapes_); }
        return *this;
    }
    void add(std::unique_ptr<Shape> s) { if (!s) throw std::invalid_argument("null"); shapes_.push_back(std::move(s)); }
    std::size_t size() const { return shapes_.size(); }
    double total_area() const { double t = 0; for (const auto& s : shapes_) t += s->area(); return t; }
    std::string largest() const {
        if (shapes_.empty()) throw std::runtime_error("empty");
        return (*std::max_element(shapes_.begin(), shapes_.end(), [](const auto& a, const auto& b) { return a->area() < b->area(); }))->name();
    }
    friend std::ostream& operator<<(std::ostream& os, const Scene& sc) {
        std::vector<const Shape*> v;
        for (const auto& s : sc.shapes_) v.push_back(s.get());
        std::sort(v.begin(), v.end(), [](const Shape* a, const Shape* b) { return a->area() < b->area(); });
        for (std::size_t i = 0; i < v.size(); ++i) {
            std::ostringstream one; one << v[i]->name() << ':' << std::fixed << std::setprecision(2) << v[i]->area();
            os << (i ? " " : "") << one.str();
        }
        return os;
    }
};
"""

FRESH_TASKS = [
    dict(id='c_pipe', lang='c', prompt=C_PIPE_PROMPT, test=C_PIPE_TEST, ref=C_PIPE_REF),
    dict(id='prolog_lists', lang='pl', prompt=PROLOG_PROMPT, test=PROLOG_TEST, ref=PROLOG_REF),
    dict(id='java_streams', lang='java', file='Report.java', prompt=JAVA_PROMPT, test=JAVA_TEST, ref=JAVA_REF),
    dict(id='cpp_oop', lang='cpp', prompt=CPP_OOP_PROMPT, test=CPP_OOP_TEST, ref=CPP_OOP_REF),
]
