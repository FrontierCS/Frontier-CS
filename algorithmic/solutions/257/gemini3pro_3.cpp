#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Maximum number of elements as per problem statement
const int MAXN = 200005;
int a[MAXN];
int n;

// Function to perform a query
void query(int l, int r, int &x, int &f) {
    if (l > r) {
        x = -1; f = -1;
        return;
    }
    cout << "? " << l << " " << r << endl;
    cin >> x >> f;
    // If we receive -1, it means invalid query or error, terminate to avoid TLE on closed stream
    if (x == -1) exit(0); 
}

// Recursive solver
// l, r: current range
// known_x, known_f: mode and frequency of the range if already known, else -1
void solve(int l, int r, int known_x, int known_f) {
    if (l > r) return;

    int x, f;
    if (known_x != -1) {
        x = known_x;
        f = known_f;
    } else {
        query(l, r, x, f);
    }

    // Base case: if frequency equals the length of the subarray, 
    // the whole subarray consists of x.
    if (f == r - l + 1) {
        for (int i = l; i <= r; ++i) {
            a[i] = x;
        }
        return;
    }

    // We split the problem based on the frequency f.
    // The range [l, r] has length L.
    // We query a prefix of length L - f: [l, r - f]
    // And a suffix of length L - f: [l + f, r]
    // Note: The length of the query ranges is (r - f) - l + 1 = (r - l + 1) - f = L - f.
    // These queries help us determine where x is located.

    int x1, f1;
    query(l, r - f, x1, f1);
    
    if (x1 == x) {
        // If the mode of the prefix is still x, then x is "dominant" in the left part.
        // We recurse on the left part with known info.
        // For the right part (the remaining suffix of size f), we treat it as a new problem.
        // The remaining part is [r - f + 1, r].
        solve(l, r - f, x1, f1);
        solve(r - f + 1, r, -1, -1);
        return;
    }
    
    int x2, f2;
    query(l + f, r, x2, f2);
    
    if (x2 == x) {
        // If the mode of the suffix is still x, then x is "dominant" in the right part.
        // Recurse on the right part with known info.
        // The remaining prefix is [l, l + f - 1].
        solve(l, l + f - 1, -1, -1);
        solve(l + f, r, x2, f2);
        return;
    }
    
    // If x is not the mode of the prefix nor the suffix, it means x is concentrated in the middle
    // or distributed such that it doesn't dominate the ends.
    // However, specifically, if the two query ranges [l, r-f] and [l+f, r] leave a gap in the middle,
    // that gap MUST be filled with x.
    // A gap exists if (r - f) < (l + f) - 1. 
    // The gap is [r - f + 1, l + f - 1].
    // This happens if 2*f > r - l + 1.
    if (2 * f > r - l + 1) {
        for (int i = r - f + 1; i <= l + f - 1; ++i) {
            a[i] = x;
        }
    }
    
    // Recurse on both sub-intervals using the information we gathered.
    // Even if ranges overlap, this is safe because the array is sorted and values are consistent.
    solve(l, r - f, x1, f1);
    solve(l + f, r, x2, f2);
}

int main() {
    // Optimization for faster I/O (though interaction requires flush)
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    solve(1, n, -1, -1);

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << a[i];
    }
    cout << endl;

    return 0;
}