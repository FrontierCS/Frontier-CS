#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

// Global variable for n to be accessible in ask function for boundary checks
long long n_global;

// Function to ask a query and handle response 0, which terminates the program.
int ask(long long x, long long y) {
    // Ensure queries are within the valid range [1, n].
    if (x < 1) x = 1;
    if (x > n_global) x = n_global;
    if (y < 1) y = 1;
    if (y > n_global) y = n_global;

    std::cout << x << " " << y << std::endl;
    int response;
    std::cin >> response;
    if (response == 0) {
        exit(0);
    }
    return response;
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n_global;

    long long a_low = 1, a_high = n_global;
    long long b_low = 1, b_high = n_global;

    while (true) {
        // If both ranges have been narrowed down to a single value, we have found the answer.
        if (a_low == a_high && b_low == b_high) {
            ask(a_low, b_low);
            // The ask function with response 0 will terminate the program.
            // This part of the code should not be reached.
            break;
        }

        // If one of the numbers is found, we can perform a simple binary search for the other.
        // This is a "safe" binary search because the ambiguity of response 3 is resolved.
        if (a_low == a_high) { // a is known
            long long mid_b = b_low + (b_high - b_low) / 2;
            int response = ask(a_low, mid_b);
            if (response == 2) { // y < b (mid_b < b)
                b_low = mid_b + 1;
            } else { // Response must be 3 (x > a or y > b). Since x=a, it must be y > b (mid_b > b).
                b_high = mid_b - 1;
            }
            continue;
        }

        if (b_low == b_high) { // b is known
            long long mid_a = a_low + (a_high - a_low) / 2;
            int response = ask(mid_a, b_low);
            if (response == 1) { // x < a (mid_a < a)
                a_low = mid_a + 1;
            } else { // Response must be 3 (x > a or y > b). Since y=b, it must be x > a (mid_a > a).
                a_high = mid_a - 1;
            }
            continue;
        }

        // If neither number is known, we query the midpoints of the current ranges.
        long long mid_a = a_low + (a_high - a_low) / 2;
        long long mid_b = b_low + (b_high - b_low) / 2;
        
        int response = ask(mid_a, mid_b);
        
        if (response == 1) { // x < a
            a_low = mid_a + 1;
        } else if (response == 2) { // y < b
            b_low = mid_b + 1;
        } else { // response == 3: x > a or y > b
            // This case is ambiguous. We don't know whether to shrink the range for 'a' or 'b'.
            // A plausible heuristic is to shrink the dimension with the larger search range.
            // This is not guaranteed to be correct in all cases, but it is a strong strategy
            // to prune the search space.
            if (a_high - a_low >= b_high - b_low) {
                a_high = mid_a - 1;
            } else {
                b_high = mid_b - 1;
            }
        }
    }

    return 0;
}