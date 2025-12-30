#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

// Function to perform a single simulation run based on a preference.
// It will binary search for the absent student and make one final guess.
// Returns `true` if the guess was correct, `false` otherwise.
bool solve_and_guess(int n, bool h_preference) {
    int L = 1, R = n;
    int h_streak = 0, d_streak = 0;

    while (L < R) {
        int mid = L + (R - L) / 2;
        std::cout << "? " << L << " " << mid << std::endl;
        int x;
        std::cin >> x;
        int len = mid - L + 1;

        bool is_honest;
        if (h_streak == 2) {
            is_honest = false;
        } else if (d_streak == 2) {
            is_honest = true;
        } else {
            is_honest = h_preference;
        }

        bool absent_in_range;
        if (is_honest) {
            // Assumed Honest response
            // True Positive: x=len, absent is out
            // True Negative: x=len-1, absent is in
            if (x == len - 1) {
                absent_in_range = true;
            } else {
                absent_in_range = false;
            }
            h_streak++;
            d_streak = 0;
        } else { // Assumed Dishonest response
            // False Positive: x=len, absent is in
            // False Negative: x=len-1, absent is out
            if (x == len) {
                absent_in_range = true;
            } else {
                absent_in_range = false;
            }
            d_streak++;
            h_streak = 0;
        }

        if (absent_in_range) {
            R = mid;
        } else {
            L = mid + 1;
        }
    }

    std::cout << "! " << L << std::endl;
    int y;
    std::cin >> y;
    return y == 1;
}

void solve_test_case() {
    int n;
    std::cin >> n;

    // First, try the Honest-preference strategy.
    if (solve_and_guess(n, true)) {
        // If correct, we are done with this test case.
        std::cout << "#" << std::endl;
        return;
    }

    // If the first guess was wrong, try the Dishonest-preference strategy.
    // We don't need to check the result, as we've used our two guesses.
    solve_and_guess(n, false);
    
    std::cout << "#" << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int t;
    std::cin >> t;
    while (t--) {
        solve_test_case();
    }

    return 0;
}