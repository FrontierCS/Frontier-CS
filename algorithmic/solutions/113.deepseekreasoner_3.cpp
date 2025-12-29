#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

// Precompute powers of 3
ll pow3[31];

// Get the basket (0,1,2) for ball i (0-indexed) from state
int get_basket(ll state, int i) {
    return (state / pow3[i]) % 3;
}

// Set the basket for ball i and return new state
ll set_basket(ll state, int i, int b) {
    int cur = get_basket(state, i);
    return state + (b - cur) * pow3[i];
}

// Get the center ball (0-indexed) of a basket given its mask (bitmask of balls)
int get_center(int mask, int N) {
    int cnt = __builtin_popcount(mask);
    if (cnt == 0) return -1;
    int rank = cnt / 2 + 1;   // 1-indexed rank of center
    int cur = 0;
    for (int i = 0; i < N; ++i) {
        if (mask & (1 << i)) {
            ++cur;
            if (cur == rank) return i;
        }
    }
    return -1; // should not happen
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    pow3[0] = 1;
    for (int i = 1; i <= 30; ++i) pow3[i] = pow3[i-1] * 3;

    int N;
    cin >> N;

    // Initial state: all balls in basket 0 (basket 1)
    ll start = 0;
    // Goal state: all balls in basket 2 (basket 3)
    ll goal = 0;
    for (int i = 0; i < N; ++i) goal += 2 * pow3[i];

    // BFS
    queue<ll> q;
    unordered_map<ll, pair<ll, pair<int,int>>> parent; // state -> {prev_state, {from, to}}
    unordered_map<ll, bool> visited;

    q.push(start);
    visited[start] = true;
    parent[start] = {-1, {-1, -1}};

    while (!q.empty()) {
        ll state = q.front(); q.pop();
        if (state == goal) break;

        // Compute masks for each basket
        vector<int> mask(3, 0);
        for (int i = 0; i < N; ++i) {
            int b = get_basket(state, i);
            mask[b] |= (1 << i);
        }

        // Try all moves a -> b (a != b)
        for (int a = 0; a < 3; ++a) {
            if (mask[a] == 0) continue;
            int x = get_center(mask[a], N); // center ball of basket a
            if (x == -1) continue;
            for (int b = 0; b < 3; ++b) {
                if (a == b) continue;
                // Check if moving ball x to basket b is valid
                int new_mask_b = mask[b] | (1 << x);
                int new_center = get_center(new_mask_b, N);
                if (new_center != x) continue; // moved ball must become center

                // Create new state
                ll new_state = set_basket(state, x, b);
                if (visited.find(new_state) != visited.end()) continue;

                visited[new_state] = true;
                parent[new_state] = {state, {a, b}};
                q.push(new_state);
            }
        }
    }

    // Reconstruct moves
    vector<pair<int,int>> moves;
    ll cur = goal;
    while (cur != start) {
        auto& p = parent[cur];
        moves.push_back(p.second);
        cur = p.first;
    }
    reverse(moves.begin(), moves.end());

    // Output
    cout << moves.size() << '\n';
    for (auto& m : moves) {
        cout << m.first + 1 << ' ' << m.second + 1 << '\n';
    }

    return 0;
}