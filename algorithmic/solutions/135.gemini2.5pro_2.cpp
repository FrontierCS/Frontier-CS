#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

// This function determines which of the three points p1, p2, p3 lies on the
// circular arc between the other two. It does so by finding which point is NOT
// part of any closest pair.
// It is designed to be deterministic, especially for the equilateral case,
// to ensure it can be used as a valid comparator for sorting.
int get_middle(int p1, int p2, int p3) {
    cout << "? " << p1 << " " << p2 << " " << p3 << endl;
    int r;
    cin >> r;
    set<int> endpoints;
    for (int i = 0; i < r; ++i) {
        int u, v;
        cin >> u >> v;
        endpoints.insert(u);
        endpoints.insert(v);
    }

    vector<int> p = {p1, p2, p3};
    for (int x : p) {
        if (endpoints.find(x) == endpoints.end()) {
            return x;
        }
    }

    // This case is reached if all three points are endpoints of at least one
    // closest pair, which happens if they form an equilateral triangle.
    // To ensure our sorting comparator remains consistent (a strict weak ordering),
    // we must have a deterministic tie-breaking rule.
    // Sorting the points and picking the minimum is a simple such rule.
    sort(p.begin(), p.end());
    return p[0];
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int k_max, n;
    cin >> k_max >> n;

    if (n <= 2) {
        cout << "! 0";
        for (int i = 1; i < n; ++i) {
            cout << " " << i;
        }
        cout << endl;
        return 0;
    }

    int p0 = 0;
    int p1 = 1;

    vector<int> s1, s2;
    for (int i = 2; i < n; ++i) {
        int middle = get_middle(i, p0, p1);
        if (middle == i) {
            // i is on one arc between p0 and p1
            s1.push_back(i);
        } else {
            // i is on the other arc
            s2.push_back(i);
        }
    }

    // Sort s1 based on proximity to p0.
    // The lambda `[&](int a, int b) { return get_middle(p0, a, b) == a; }`
    // serves as a "less than" comparator. It returns true if 'a' comes before 'b'
    // in the sequence starting from p0.
    sort(s1.begin(), s1.end(), [&](int a, int b) {
        return get_middle(p0, a, b) == a;
    });

    // Same sorting logic for s2.
    sort(s2.begin(), s2.end(), [&](int a, int b) {
        return get_middle(p0, a, b) == a;
    });

    cout << "! " << p0;
    for (int x : s1) {
        cout << " " << x;
    }
    cout << " " << p1;
    // s2 contains points on the "other" arc. When sorted relative to p0, the order
    // is moving away from p0. To complete the full circle from p1 back to p0,
    // we need to list these points in reverse order of their distance from p0.
    reverse(s2.begin(), s2.end());
    for (int x : s2) {
        cout << " " << x;
    }
    cout << endl;

    return 0;
}