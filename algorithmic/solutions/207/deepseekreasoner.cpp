#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);

    int N;
    cin >> N;
    vector<int> a(N);
    for (int i = 0; i < N; ++i) {
        cin >> a[i];
    }

    vector<int> pos(N);
    int correct_count = 0;
    for (int i = 0; i < N; ++i) {
        pos[a[i]] = i;
        if (a[i] == i) ++correct_count;
    }

    vector<int> dist(N, 0);
    using Pair = pair<int, int>;
    priority_queue<Pair, vector<Pair>, greater<Pair>> pq; // min-heap by distance
    for (int i = 0; i < N; ++i) {
        if (a[i] != i) {
            dist[i] = abs(i - pos[i]);
            pq.push({dist[i], i});
        }
    }

    int M;
    cin >> M;
    vector<int> X(M), Y(M);
    for (int j = 0; j < M; ++j) {
        cin >> X[j] >> Y[j];
    }

    vector<pair<int, int>> our_swaps;
    long long total_dist = 0;
    int R = 0;
    bool sorted = false;

    // Helper function to swap two indices and update all structures
    auto swap_indices = [&](int x, int y) {
        if (x == y) return;
        int vx = a[x], vy = a[y];
        vector<int> idxs = {x, y, vx, vy};
        sort(idxs.begin(), idxs.end());
        idxs.erase(unique(idxs.begin(), idxs.end()), idxs.end());

        // Update correct_count for old state
        for (int i : idxs) {
            if (a[i] == i) --correct_count;
        }

        // Perform swap
        swap(a[x], a[y]);
        pos[vx] = y;
        pos[vy] = x;

        // Update correct_count for new state
        for (int i : idxs) {
            if (a[i] == i) ++correct_count;
        }

        // Push new entries for misplaced indices
        for (int i : idxs) {
            if (a[i] != i) {
                int d = abs(i - pos[i]);
                dist[i] = d;
                pq.push({d, i});
            }
        }
    };

    for (int k = 0; k < M; ++k) {
        // Jerry's move
        swap_indices(X[k], Y[k]);

        if (correct_count == N) {
            // Array sorted after Jerry's swap
            our_swaps.emplace_back(0, 0); // dummy swap
            R = k + 1;
            sorted = true;
            break;
        }

        // Our move: pick misplaced index with smallest distance
        int i = -1;
        while (!pq.empty()) {
            auto [d, idx] = pq.top();
            pq.pop();
            if (a[idx] != idx && dist[idx] == d) {
                i = idx;
                break;
            }
        }

        // Fallback (should not happen)
        if (i == -1) {
            for (int j = 0; j < N; ++j) {
                if (a[j] != j) {
                    i = j;
                    break;
                }
            }
        }

        int j = pos[i]; // current position of value i
        our_swaps.emplace_back(i, j);
        total_dist += abs(i - j);
        swap_indices(i, j);

        if (correct_count == N) {
            R = k + 1;
            sorted = true;
            break;
        }
    }

    if (!sorted) {
        // Used all M rounds
        R = M;
    }

    // Output
    cout << R << "\n";
    for (auto [u, v] : our_swaps) {
        cout << u << " " << v << "\n";
    }
    cout << (long long)R * total_dist << "\n";

    return 0;
}