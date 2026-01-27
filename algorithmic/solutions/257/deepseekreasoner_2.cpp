#include <iostream>
#include <vector>
#include <utility>
#include <cstdlib>

using namespace std;

// Global array to store the result
int n;
vector<int> a;

// Function to query the interactive judge
// Returns {mode, frequency}
pair<int, int> query(int l, int r) {
    if (l > r) return {-1, -1};
    cout << "? " << l << " " << r << endl;
    int x, f;
    cin >> x >> f;
    if (x == -1) exit(0); // Exit immediately if invalid query or error
    return {x, f};
}

// Recursive function to solve for range [l, r]
// known_x and known_f are the results of querying [l, r] if already known, else -1
void solve(int l, int r, int known_x, int known_f) {
    if (l > r) return;

    int x = known_x;
    int f = known_f;

    // If we don't have the mode/frequency for this range, query it
    if (x == -1) {
        pair<int, int> res = query(l, r);
        x = res.first;
        f = res.second;
    }

    // If the frequency equals the length of the range, the range is uniform filled with x
    if (f == r - l + 1) {
        for (int i = l; i <= r; ++i) {
            a[i] = x;
        }
        return;
    }

    int mid = l + (r - l) / 2;

    // We query the left child to get information
    pair<int, int> left_res = query(l, mid);
    int xL = left_res.first;
    int fL = left_res.second;

    // Optimization: Check if we can infer that the right child is fully filled with the parent mode x.
    // This happens if the parent mode x is the same as left mode xL, 
    // and the remaining occurrences of x (f - fL) exactly cover the size of the right child.
    // Note: This relies on the property that identical elements are contiguous (sorted array).
    bool right_is_full = false;
    if (xL == x && (f - fL == r - mid)) {
        right_is_full = true;
    }

    // Solve the left subproblem recursively, passing the already obtained query result
    solve(l, mid, xL, fL);

    // Solve the right subproblem
    if (right_is_full) {
        // Avoid querying right child if we inferred it's full of x
        for (int i = mid + 1; i <= r; ++i) {
            a[i] = x;
        }
    } else {
        // Otherwise, we must solve normally (will trigger a query inside)
        solve(mid + 1, r, -1, -1);
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    a.resize(n + 1);

    // Start the recursive solution
    solve(1, n, -1, -1);

    // Output the result
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << a[i];
    }
    cout << endl;

    return 0;
}