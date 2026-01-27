#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <unordered_set>

using namespace std;

const int MAX_OPS = 50000;
const int MAX_VISITED = 10000;

int main() {
    int N;
    cin >> N;
    vector<int> A(N), B(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    for (int i = 0; i < N; ++i) cin >> B[i];

    long long sumA = accumulate(A.begin(), A.end(), 0LL);
    long long sumB = accumulate(B.begin(), B.end(), 0LL);
    if (sumA != sumB) {
        cout << "No\n";
        return 0;
    }

    vector<int> d(N);
    for (int i = 0; i < N; ++i) d[i] = A[i] - B[i];

    bool done = true;
    for (int i = 0; i < N; ++i) if (d[i] != 0) { done = false; break; }
    if (done) {
        cout << "Yes\n0\n";
        return 0;
    }

    // Precompute constants C for each pair (i,j) with i<j
    vector<vector<long long>> C(N, vector<long long>(N));
    for (int i = 0; i < N; ++i)
        for (int j = i+1; j < N; ++j)
            C[i][j] = B[j] - B[i] - 1;

    auto hash_d = [&](const vector<int>& vec) -> size_t {
        size_t h = 0;
        for (int x : vec) h = h * 123456789 + (x + 100);
        return h;
    };

    unordered_set<size_t> visited;
    visited.insert(hash_d(d));

    vector<pair<int,int>> ops;
    int steps = 0;
    bool progress = true;

    while (steps < MAX_OPS) {
        long long cur_sum_sq = 0;
        for (int i = 0; i < N; ++i) cur_sum_sq += 1LL * d[i] * d[i];

        int best_i = -1, best_j = -1;
        long long best_new_sum_sq = cur_sum_sq; // start with current

        for (int i = 0; i < N; ++i) {
            for (int j = i+1; j < N; ++j) {
                long long c = C[i][j];
                long long new_di = d[j] + c;
                long long new_dj = d[i] - c;
                long long new_sum_sq = cur_sum_sq
                    - (1LL*d[i]*d[i] + 1LL*d[j]*d[j])
                    + (new_di*new_di + new_dj*new_dj);
                if (new_sum_sq < best_new_sum_sq) {
                    best_new_sum_sq = new_sum_sq;
                    best_i = i;
                    best_j = j;
                }
            }
        }

        if (best_new_sum_sq >= cur_sum_sq) {
            // No improving move found
            break;
        }

        // Check if the new state was visited (skip if it doesn't improve enough)
        vector<int> d_new = d;
        d_new[best_i] = d[best_j] + C[best_i][best_j];
        d_new[best_j] = d[best_i] - C[best_i][best_j];
        size_t h_new = hash_d(d_new);
        if (visited.count(h_new)) {
            // already visited, try to find another move? for simplicity break
            break;
        }

        // Apply the move
        int &Ai = A[best_i], &Aj = A[best_j];
        int new_Ai = Aj - 1;
        int new_Aj = Ai + 1;
        Ai = new_Ai;
        Aj = new_Aj;

        d[best_i] = d_new[best_i];
        d[best_j] = d_new[best_j];
        ops.emplace_back(best_i+1, best_j+1);
        ++steps;

        // Check if done
        done = true;
        for (int i = 0; i < N; ++i) if (d[i] != 0) { done = false; break; }
        if (done) break;

        visited.insert(h_new);
        if (visited.size() > MAX_VISITED) visited.clear();
    }

    done = true;
    for (int i = 0; i < N; ++i) if (d[i] != 0) done = false;

    if (done) {
        cout << "Yes\n";
        cout << ops.size() << "\n";
        for (auto &p : ops) cout << p.first << " " << p.second << "\n";
    } else {
        cout << "No\n";
    }

    return 0;
}