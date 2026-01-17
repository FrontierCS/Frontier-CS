#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <numeric>
#include <cstdlib>
#include <tuple>

using namespace std;

typedef long long ll;

const int DUMMY = 0; // dummy swap (0,0)

// Update status of index i after changes to a and pos.
// a: current array, pos: position of each value, cur_dist: current distance for i if misplaced else -1, pq: priority queue, misplaced_cnt: counter
void update_idx(int i, const vector<int>& a, const vector<int>& pos, vector<int>& cur_dist, priority_queue<pair<int,int>, vector<pair<int,int>>, greater<pair<int,int>>>& pq, int& misplaced_cnt) {
    bool mis = (a[i] != i);
    if (!mis) {
        if (cur_dist[i] != -1) {
            cur_dist[i] = -1;
            misplaced_cnt--;
        }
        return;
    }
    int d = abs(i - pos[i]);
    if (cur_dist[i] == -1) {
        misplaced_cnt++;
    }
    if (cur_dist[i] != d) {
        cur_dist[i] = d;
        pq.push({d, i});
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<int> S(N);
    vector<int> orig_pos(N); // original position of each value
    for (int i = 0; i < N; i++) {
        cin >> S[i];
        orig_pos[S[i]] = i;
    }

    int M;
    cin >> M;
    vector<int> X(M), Y(M);
    for (int i = 0; i < M; i++) {
        cin >> X[i] >> Y[i];
    }

    // ----- Greedy simulation -----
    vector<int> a = S;
    vector<int> pos = orig_pos; // pos[v] = current index of value v
    vector<int> cur_dist(N, -1);
    int misplaced_cnt = 0;
    priority_queue<pair<int,int>, vector<pair<int,int>>, greater<pair<int,int>>> pq;
    for (int i = 0; i < N; i++) {
        if (a[i] != i) {
            int d = abs(i - pos[i]);
            cur_dist[i] = d;
            pq.push({d, i});
            misplaced_cnt++;
        }
    }

    vector<pair<int,int>> our_swaps;
    our_swaps.reserve(M);
    int R = -1;
    bool sorted_early = false;

    for (int k = 0; k < M; k++) {
        // Jerry's swap
        int x = X[k], y = Y[k];
        if (x != y) {
            int vx = a[x], vy = a[y];
            swap(a[x], a[y]);
            pos[vx] = y;
            pos[vy] = x;
            update_idx(x, a, pos, cur_dist, pq, misplaced_cnt);
            update_idx(y, a, pos, cur_dist, pq, misplaced_cnt);
        }

        // Remove stale entries from pq
        while (!pq.empty()) {
            auto [d, i] = pq.top();
            if (cur_dist[i] != d || a[i] == i) {
                pq.pop();
            } else {
                break;
            }
        }

        if (misplaced_cnt == 0) {
            // already sorted, do dummy swap
            our_swaps.emplace_back(DUMMY, DUMMY);
            sorted_early = true;
            R = k + 1;
            break;
        }

        // Choose the misplaced index with smallest distance
        int i = pq.top().second;
        int j = pos[i]; // where value i is
        our_swaps.emplace_back(i, j);

        // Perform our swap
        int vi = a[i], vj = a[j];
        swap(a[i], a[j]);
        pos[vi] = j;
        pos[vj] = i;
        update_idx(i, a, pos, cur_dist, pq, misplaced_cnt);
        update_idx(j, a, pos, cur_dist, pq, misplaced_cnt);

        if (misplaced_cnt == 0) {
            sorted_early = true;
            R = k + 1;
            break;
        }
    }

    if (sorted_early) {
        // Compute total efficiency V
        ll sum_dist = 0;
        for (auto& sw : our_swaps) {
            sum_dist += abs(sw.first - sw.second);
        }
        ll V = (ll)R * sum_dist;

        // Output
        cout << R << "\n";
        for (int k = 0; k < R; k++) {
            cout << our_swaps[k].first << " " << our_swaps[k].second << "\n";
        }
        cout << V << "\n";
        return 0;
    }

    // ----- Fallback: use all M rounds, compute K and decompose -----
    // Compute J_total: permutation after applying all Jerry swaps to identity
    vector<int> J_total(N);
    iota(J_total.begin(), J_total.end(), 0);
    for (int k = 0; k < M; k++) {
        swap(J_total[X[k]], J_total[Y[k]]);
    }
    // Inverse of J_total
    vector<int> invJ(N);
    for (int i = 0; i < N; i++) {
        invJ[J_total[i]] = i;
    }
    // Compute K_idx: K = invJ * orig_pos (as permutation on indices)
    vector<int> K_idx(N);
    for (int v = 0; v < N; v++) {
        K_idx[v] = invJ[orig_pos[v]];
    }

    // Find cycles of K_idx
    vector<bool> visited(N, false);
    vector<vector<int>> cycles;
    for (int i = 0; i < N; i++) {
        if (visited[i]) continue;
        vector<int> cyc;
        int cur = i;
        while (!visited[cur]) {
            visited[cur] = true;
            cyc.push_back(cur);
            cur = K_idx[cur];
        }
        if (cyc.size() > 1) {
            cycles.push_back(move(cyc));
        }
    }

    // Generate swaps for each cycle using median heuristic
    vector<pair<int,int>> fallback_swaps;
    for (auto& cyc : cycles) {
        // Find best pivot (median by value to minimize sum of distances)
        // Since values are indices themselves, we can compute sum of absolute differences.
        // We'll try each element as pivot and choose the one with smallest sum.
        int best_pivot_idx = 0;
        ll best_sum = 1e18;
        for (size_t p = 0; p < cyc.size(); p++) {
            ll s = 0;
            for (int val : cyc) {
                s += abs(cyc[p] - val);
            }
            if (s < best_sum) {
                best_sum = s;
                best_pivot_idx = p;
            }
        }
        // Rotate cycle so that pivot is first
        rotate(cyc.begin(), cyc.begin() + best_pivot_idx, cyc.end());
        int pivot = cyc[0];
        for (size_t i = 1; i < cyc.size(); i++) {
            fallback_swaps.emplace_back(pivot, cyc[i]);
        }
    }

    int L = fallback_swaps.size();
    // We need M swaps total; pad with dummy swaps
    our_swaps = move(fallback_swaps);
    our_swaps.resize(M, {DUMMY, DUMMY});

    // Compute total efficiency V
    ll sum_dist = 0;
    for (auto& sw : our_swaps) {
        sum_dist += abs(sw.first - sw.second);
    }
    ll V = (ll)M * sum_dist;

    // Output
    cout << M << "\n";
    for (int k = 0; k < M; k++) {
        cout << our_swaps[k].first << " " << our_swaps[k].second << "\n";
    }
    cout << V << "\n";

    return 0;
}