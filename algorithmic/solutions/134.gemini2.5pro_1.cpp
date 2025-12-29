#include <iostream>
#include <vector>
#include <algorithm>

long long N;

// Query function that handles termination on response 0
int query(long long x, long long y) {
    std::cout << x << " " << y << std::endl;
    int response;
    std::cin >> response;
    if (response == 0) {
        exit(0);
    }
    return response;
}

// The recursive solver
void solve(long long la, long long ra, long long lb, long long rb) {
    // Base case: if the search space is a single point, we've found the answer.
    if (la == ra && lb == rb) {
        query(la, lb); // This must return 0.
        return;
    }

    // Prioritize shrinking the larger dimension
    if (ra - la >= rb - lb) {
        long long mid_a = la + (ra - la) / 2;
        int res = query(mid_a, rb);

        if (res == 1) { // mid_a < a
            solve(mid_a + 1, ra, lb, rb);
        } else { // res must be 3: mid_a > a OR rb > b
            // We need to distinguish: is b == rb?
            int check_res = query(1, rb);
            if (check_res == 1) { // 1 < a implies b must be rb
                // From the first query, it must be that mid_a > a
                solve(la, mid_a, rb, rb);
            } else { // check_res must be 3 (1 > a is false), so rb > b
                // We know b < rb. Find a new, tighter upper bound for b.
                long long new_rb_l = lb, new_rb_r = rb - 1, new_rb = rb - 1;
                while (new_rb_l <= new_rb_r) {
                    long long mid_b = new_rb_l + (new_rb_r - new_rb_l) / 2;
                    if (mid_b < lb) break; // Should not happen with proper bounds
                    int b_search_res = query(1, mid_b);
                    if (b_search_res == 2) { // mid_b < b
                        new_rb_l = mid_b + 1;
                    } else { // mid_b >= b
                        new_rb = mid_b;
                        new_rb_r = mid_b - 1;
                    }
                }
                solve(la, ra, lb, new_rb);
            }
        }
    } else { // Symmetric logic for shrinking b's range
        long long mid_b = lb + (rb - lb) / 2;
        int res = query(ra, mid_b);

        if (res == 2) { // mid_b < b
            solve(la, ra, mid_b + 1, rb);
        } else { // res must be 3: ra > a OR mid_b > b
            // Distinguish: is a == ra?
            int check_res = query(ra, 1);
            if (check_res == 2) { // 1 < b implies a must be ra
                // From the first query, it must be that mid_b > b
                solve(ra, ra, lb, mid_b);
            } else { // check_res must be 3 (1 > b is false), so ra > a
                // We know a < ra. Find a new, tighter upper bound for a.
                long long new_ra_l = la, new_ra_r = ra - 1, new_ra = ra - 1;
                while (new_ra_l <= new_ra_r) {
                    long long mid_a = new_ra_l + (new_ra_r - new_ra_l) / 2;
                     if (mid_a < la) break;
                    int a_search_res = query(mid_a, 1);
                    if (a_search_res == 1) { // mid_a < a
                        new_ra_l = mid_a + 1;
                    } else { // mid_a >= a
                        new_ra = mid_a;
                        new_ra_r = mid_a - 1;
                    }
                }
                solve(la, new_ra, lb, rb);
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> N;
    solve(1, N, 1, N);

    return 0;
}