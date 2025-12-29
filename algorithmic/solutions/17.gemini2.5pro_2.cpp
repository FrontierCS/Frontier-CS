#include <iostream>

// Function to perform a query
int ask(int l, int r) {
    std::cout << "? " << l << " " << r << std::endl;
    int result;
    std::cin >> result;
    return result;
}

// Function to output the answer
void answer(int x) {
    std::cout << "! " << x << std::endl;
}

// Main logic for a single test case
void solve() {
    int n;
    std::cin >> n;

    int s = ask(1, n);

    if (s > 1 && ask(1, s) == s) {
        // Position of n is in [1, s-1].
        // The position of n is the largest p in [1, s-1] for which ask(p, s) returns s.
        // We can find this using a binary search for the "last true" value.
        int L = 1, R = s - 1;
        int ans = 1;
        while (L <= R) {
            int M = L + (R - L) / 2;
            if (ask(M, s) == s) {
                ans = M;
                L = M + 1;
            } else {
                R = M - 1;
            }
        }
        answer(ans);
    } else {
        // Position of n is in [s+1, n].
        // This branch also correctly handles s=1.
        // The position of n is the smallest p in [s+1, n] for which ask(s, p) returns s.
        // We can find this using a binary search for the "first true" value.
        int L = s + 1, R = n;
        int ans = n;
        while (L <= R) {
            int M = L + (R - L) / 2;
            if (ask(s, M) == s) {
                ans = M;
                R = M - 1;
            } else {
                L = M + 1;
            }
        }
        answer(ans);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}