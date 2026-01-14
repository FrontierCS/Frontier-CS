#include <iostream>
#include <vector>
#include <queue>
#include <cstdlib>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);

    int N;
    cin >> N;
    vector<int> A(N), pos(N);
    for (int i = 0; i < N; ++i) {
        cin >> A[i];
        pos[A[i]] = i;
    }

    vector<bool> incorrect(N, false);
    queue<int> q;
    for (int i = 0; i < N; ++i) {
        if (A[i] != i) {
            incorrect[i] = true;
            q.push(i);
        }
    }

    int M;
    cin >> M;
    vector<pair<int, int>> jerry(M);
    for (int j = 0; j < M; ++j) {
        cin >> jerry[j].first >> jerry[j].second;
    }

    // Helper functions to maintain incorrect set
    auto update_incorrect = [&](int idx) {
        bool is_incorrect = (A[idx] != idx);
        if (is_incorrect && !incorrect[idx]) {
            incorrect[idx] = true;
            q.push(idx);
        } else if (!is_incorrect && incorrect[idx]) {
            incorrect[idx] = false;
        }
    };

    auto clean_q = [&]() {
        while (!q.empty() && !incorrect[q.front()]) {
            q.pop();
        }
    };

    vector<pair<int, int>> our_swaps;
    long long total_cost = 0;
    int R = 0;
    bool sorted = false;

    for (int k = 0; k < M; ++k) {
        // Jerry's move
        int x = jerry[k].first, y = jerry[k].second;
        if (x != y) {
            int val_x = A[x], val_y = A[y];
            swap(A[x], A[y]);
            swap(pos[val_x], pos[val_y]);
            update_incorrect(x);
            update_incorrect(y);
        }

        clean_q();
        if (q.empty()) {
            // Already sorted after Jerry's swap
            our_swaps.emplace_back(0, 0);
            total_cost += 0;
            R = k + 1;
            sorted = true;
            break;
        }

        // Our move: pick the first incorrect index
        int i = q.front(); q.pop();
        incorrect[i] = false;
        int j = pos[i]; // current position of value i
        // Perform swap (i, j)
        if (i != j) {
            int val_i = A[i], val_j = A[j];
            swap(A[i], A[j]);
            swap(pos[val_i], pos[val_j]);
            update_incorrect(i);
            update_incorrect(j);
            int cost = abs(i - j);
            total_cost += cost;
            our_swaps.emplace_back(i, j);
        } else {
            // Should not happen, but safety
            our_swaps.emplace_back(i, i);
        }

        clean_q();
        if (q.empty()) {
            R = k + 1;
            sorted = true;
            break;
        }
    }

    if (!sorted) {
        // Fallback: should not happen due to problem guarantee,
        // but if it does, we output dummy swaps for all M rounds
        R = M;
        our_swaps.clear();
        total_cost = 0;
        for (int k = 0; k < M; ++k) {
            our_swaps.emplace_back(0, 0);
        }
    }

    // Output
    cout << R << "\n";
    for (int k = 0; k < R; ++k) {
        cout << our_swaps[k].first << " " << our_swaps[k].second << "\n";
    }
    long long V = R * total_cost;
    cout << V << "\n";

    return 0;
}