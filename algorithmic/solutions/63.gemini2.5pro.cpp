#include <iostream>
#include <vector>
#include <numeric>

// Function to perform a query
int ask_query(int M, const std::vector<int>& directions) {
    std::cout << 0;
    for (int i = 0; i < M; ++i) {
        std::cout << " " << directions[i];
    }
    std::cout << std::endl;
    int response;
    std::cin >> response;
    return response;
}

// Function to submit the final answer
void submit_answer(int A, int B) {
    std::cout << 1 << " " << A << " " << B << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N, M;
    std::cin >> N >> M;

    std::vector<std::pair<int, int>> edges(M);
    for (int i = 0; i < M; ++i) {
        std::cin >> edges[i].first >> edges[i].second;
    }

    std::vector<int> directions(M);

    // Initial query to determine if A < B
    // Orient U_i -> V_i (min -> max) for all edges
    for (int i = 0; i < M; ++i) {
        directions[i] = 0;
    }
    bool A_is_smaller = ask_query(M, directions);

    int A, B;

    if (A_is_smaller) { // Case A < B
        // Find B first. B is in [1, N-1].
        // Query Q_A(mid) tells if B > mid.
        int b_low = 1, b_high = N - 1, found_B = N - 1;
        while (b_low <= b_high) {
            int mid = b_low + (b_high - b_low) / 2;
            for (int i = 0; i < M; ++i) {
                int u = edges[i].first;
                int v = edges[i].second;
                if (v <= mid) { // Both in S1
                    directions[i] = 1; // max -> min
                } else if (u > mid) { // Both in S2
                    directions[i] = 0; // min -> max
                } else { // u <= mid < v, across partitions S1->S2
                    directions[i] = 0;
                }
            }
            if (ask_query(M, directions) == 1) { // B > mid
                b_low = mid + 1;
            } else { // B <= mid
                found_B = mid;
                b_high = mid - 1;
            }
        }
        B = found_B;

        // Find A. B is now known. A is in [0, B-1].
        // Query Q_B(mid) tells if A > mid.
        int a_low = 0, a_high = B - 1, found_A = 0;
        while (a_low <= a_high) {
            int mid = a_low + (a_high - a_low) / 2;
            for (int i = 0; i < M; ++i) {
                int u = edges[i].first;
                int v = edges[i].second;
                 if (v <= mid) { // Both in S1
                    directions[i] = 0; // min -> max
                } else if (u > mid) { // Both in S2
                    directions[i] = 0; // min -> max
                } else { // u <= mid < v, across partitions S2->S1
                    directions[i] = 1;
                }
            }
            if (ask_query(M, directions) == 1) { // A > mid
                found_A = mid + 1;
                a_low = mid + 1;
            } else { // A <= mid
                a_high = mid - 1;
            }
        }
        A = found_A;

    } else { // Case B < A
        // Find B. B is in [0, N-2].
        // Query Q_A'(mid) tells if B > mid.
        int b_low = 0, b_high = N - 2, found_B = 0;
        while (b_low <= b_high) {
            int mid = b_low + (b_high - b_low) / 2;
            for (int i = 0; i < M; ++i) {
                int u = edges[i].first;
                int v = edges[i].second;
                if (v <= mid) { // Both in S1
                    directions[i] = 0; // min -> max
                } else if (u > mid) { // Both in S2
                    directions[i] = 1; // max -> min
                } else { // u <= mid < v, across partitions S1->S2
                    directions[i] = 0;
                }
            }
            if (ask_query(M, directions) == 1) { // B > mid
                found_B = mid + 1;
                b_low = mid + 1;
            } else { // B <= mid
                b_high = mid - 1;
            }
        }
        B = found_B;

        // Find A. B is known. A is in [B+1, N-1].
        // Query Q_B'(mid) tells if A <= mid.
        int a_low = B + 1, a_high = N - 1, found_A = N-1;
        while (a_low <= a_high) {
            int mid = a_low + (a_high - a_low) / 2;
            for (int i = 0; i < M; ++i) {
                int u = edges[i].first;
                int v = edges[i].second;
                if (v <= mid) { // Both in S1
                    directions[i] = 1; // max -> min
                } else if (u > mid) { // Both in S2
                    directions[i] = 1; // max -> min
                } else { // u <= mid < v, across partitions S1->S2
                    directions[i] = 0;
                }
            }
            if (ask_query(M, directions) == 1) { // A <= mid
                found_A = mid;
                a_high = mid - 1;
            } else { // A > mid
                a_low = mid + 1;
            }
        }
        A = found_A;
    }

    submit_answer(A, B);

    return 0;
}