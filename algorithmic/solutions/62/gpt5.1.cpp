#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<vector<int>> st;          // stacks 1..n+1, bottom -> top
vector<int> lockedDepth;         // lockedDepth[i]: number of balls locked at bottom of pillar i
vector<pair<int,int>> ops;       // operations (x, y)

inline void move_ball(int from, int to) {
    int color = st[from].back();
    st[from].pop_back();
    st[to].push_back(color);
    ops.emplace_back(from, to);
}

int find_dest(int exclude) {
    for (int i = 1; i <= n + 1; ++i) {
        if (i == exclude) continue;
        if ((int)st[i].size() < m) return i;
    }
    return -1; // should never happen if logic is correct
}

void process_color(int c) {
    int target = c;
    int src = -1;
    int best_above = INT_MAX;

    // Find column with target color in the unprocessed region with minimal "above" count
    for (int j = 1; j <= n + 1; ++j) {
        int sz = (int)st[j].size();
        for (int k = sz - 1; k >= lockedDepth[j]; --k) {
            if (st[j][k] == target) {
                int above = sz - 1 - k;
                if (above < best_above) {
                    best_above = above;
                    src = j;
                }
                break; // only need nearest from top in this column
            }
        }
    }

    // Bring target ball to top of src
    while (st[src].back() != target) {
        int dest = find_dest(src);
        move_ball(src, dest);
    }

    if (src == c) {
        // Move target temporarily to helper
        int helper = find_dest(src);
        move_ball(src, helper);

        // Clear column c down to lockedDepth[c]
        while ((int)st[c].size() > lockedDepth[c]) {
            int dest = find_dest(c);
            move_ball(c, dest);
        }

        // Place target ball onto column c
        move_ball(helper, c);
    } else {
        // Clear column c down to lockedDepth[c]
        while ((int)st[c].size() > lockedDepth[c]) {
            int dest = find_dest(c);
            move_ball(c, dest);
        }

        // Move target from src to c
        move_ball(src, c);
    }

    lockedDepth[c]++;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> m)) return 0;

    st.assign(n + 2, {});
    lockedDepth.assign(n + 2, 0);

    for (int i = 1; i <= n; ++i) {
        st[i].reserve(m);
        for (int j = 0; j < m; ++j) {
            int x;
            cin >> x;
            st[i].push_back(x); // input is bottom to top
        }
    }
    // pillar n+1 is initially empty

    for (int layer = 1; layer <= m; ++layer) {
        for (int c = 1; c <= n; ++c) {
            process_color(c);
        }
    }

    cout << ops.size() << '\n';
    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }

    return 0;
}