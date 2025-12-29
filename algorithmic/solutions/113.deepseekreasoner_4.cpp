#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

int N;

// Encode state: each ball's basket (0,1,2) into a base-3 number
ll encode(const vector<int>& state) {
    ll res = 0;
    for (int i = 0; i < N; i++) {
        res = res * 3 + state[i];
    }
    return res;
}

vector<int> decode(ll code, int n) {
    vector<int> state(n);
    for (int i = n - 1; i >= 0; i--) {
        state[i] = code % 3;
        code /= 3;
    }
    return state;
}

// Get the center ball number from a sorted list of balls
int getCenter(const vector<int>& balls) {
    int sz = balls.size();
    return balls[sz / 2];   // sz/2 works for all sz >= 1
}

// Check if moving ball x from basket a to basket b is valid
bool isValidMove(const vector<int>& state, int a, int b, int x) {
    int cnt = 0;      // number of balls in b with value < x
    int sz_b = 0;
    for (int i = 0; i < N; i++) {
        if (state[i] == b) {
            sz_b++;
            if (i + 1 < x) cnt++;
        }
    }
    int required = (sz_b + 1) / 2;
    return cnt == required;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> N;
    vector<int> start(N, 0);  // all in basket 0 (basket 1)
    ll start_code = encode(start);
    vector<int> goal_vec(N, 2); // all in basket 2 (basket 3)
    ll goal_code = encode(goal_vec);

    if (start_code == goal_code) {
        cout << 0 << endl;
        return 0;
    }

    // BFS
    unordered_map<ll, pair<ll, pair<int, int>>> parent; // state -> {prev_state, {from, to}}
    queue<ll> q;
    q.push(start_code);
    parent[start_code] = { -1, {-1, -1} };

    while (!q.empty()) {
        ll cur = q.front(); q.pop();
        vector<int> state = decode(cur, N);

        // Try all possible moves (a -> b)
        for (int a = 0; a < 3; a++) {
            // Collect balls in basket a
            vector<int> balls_a;
            for (int i = 0; i < N; i++) {
                if (state[i] == a) balls_a.push_back(i + 1);
            }
            if (balls_a.empty()) continue;
            sort(balls_a.begin(), balls_a.end());
            int center_ball = getCenter(balls_a);  // ball number (1-indexed)

            for (int b = 0; b < 3; b++) {
                if (a == b) continue;
                if (!isValidMove(state, a, b, center_ball)) continue;

                // Apply the move
                vector<int> new_state = state;
                new_state[center_ball - 1] = b;
                ll new_code = encode(new_state);
                if (parent.find(new_code) != parent.end()) continue;

                parent[new_code] = { cur, {a + 1, b + 1} }; // store baskets as 1-indexed
                if (new_code == goal_code) {
                    // Reconstruct the sequence
                    vector<pair<int, int>> moves;
                    ll code = new_code;
                    while (code != start_code) {
                        moves.push_back(parent[code].second);
                        code = parent[code].first;
                    }
                    reverse(moves.begin(), moves.end());
                    cout << moves.size() << endl;
                    for (auto& p : moves) {
                        cout << p.first << " " << p.second << "\n";
                    }
                    return 0;
                }
                q.push(new_code);
            }
        }
    }

    // No solution found (should not happen for given constraints)
    cout << 0 << endl;
    return 0;
}