#include <iostream>

// Function to ask a query. It prints the query to stdout, reads the response from stdin,
// and ensures the output stream is flushed.
int ask(int l, int r) {
    std::cout << "? " << l << " " << r << std::endl;
    int result;
    std::cin >> result;
    return result;
}

// Function to print the final answer and flush the output stream.
void answer(int x) {
    std::cout << "! " << x << std::endl;
}

// The main logic for solving a single test case.
void solve() {
    int n;
    std::cin >> n;

    // First, find the position of the second largest element in the whole permutation (n-1).
    // This position 's' will be our reference point.
    int s = ask(1, n);

    // Determine if the position of 'n' is to the left or right of 's'.
    // We query the range [1, s] (if valid) to find this out.
    bool n_is_on_the_left = false;
    if (s > 1) {
        int s_check = ask(1, s);
        // If the second largest element in [1, s] is at 's', it implies
        // a larger element (which must be 'n') exists in [1, s-1].
        if (s_check == s) {
            n_is_on_the_left = true;
        }
    }
    // If s == 1, n must be on the right, so n_is_on_the_left remains false.

    if (n_is_on_the_left) {
        // 'n' is in [1, s-1]. Binary search for it using 's' as a reference.
        int L = 1, R = s - 1;
        while (L < R) {
            int mid = L + (R - L) / 2; // Floor mid
            // Test if 'n' is in the right half of the search space: [mid+1, R].
            // Querying [mid+1, s] reveals this.
            int res = ask(mid + 1, s);
            if (res == s) {
                // If 's' is the second max, 'n' is in [mid+1, s-1].
                // So, we narrow our search to the right half.
                L = mid + 1;
            } else {
                // Otherwise, 'n' must be in the left half [L, mid].
                R = mid;
            }
        }
        answer(L);
    } else {
        // 'n' is in [s+1, n]. Binary search for it using 's' as a reference.
        int L = s + 1, R = n;
        while (L < R) {
            int mid = L + (R - L + 1) / 2; // Ceiling mid to avoid infinite loops
            // Test if 'n' is in the left half of the search space: [L, mid-1].
            // Querying [s, mid-1] reveals this.
            int res = ask(s, mid - 1);
            if (res == s) {
                // If 's' is the second max, 'n' is in [s+1, mid-1].
                // So, we narrow our search to the left half.
                R = mid - 1;
            } else {
                // Otherwise, 'n' must be in the right half [mid, R].
                L = mid;
            }
        }
        answer(L);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int T;
    std::cin >> T;
    while (T--) {
        solve();
    }

    return 0;
}