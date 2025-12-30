#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int to;
    char ch;
};

static inline int encode4(const string& s, int pos) {
    int id = 0;
    for (int k = 0; k < 4; k++) id = id * 26 + (s[pos + k] - 'A');
    return id;
}

static inline string decode4(int id) {
    char buf[4];
    for (int k = 3; k >= 0; k--) {
        buf[k] = char('A' + (id % 26));
        id /= 26;
    }
    return string(buf, buf + 4);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    int si, sj;
    cin >> si >> sj;

    vector<string> grid(N);
    for (int i = 0; i < N; i++) cin >> grid[i];

    vector<vector<pair<int,int>>> pos(26);
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            pos[grid[i][j] - 'A'].push_back({i, j});
        }
    }

    const int V = 26 * 26 * 26 * 26;
    vector<vector<Edge>> adj(V);
    adj.shrink_to_fit();

    vector<string> words(M);
    for (int k = 0; k < M; k++) {
        cin >> words[k];
        const string& w = words[k];
        int u = encode4(w, 0);
        int v = encode4(w, 1);
        adj[u].push_back({v, w[4]});
    }

    auto build_trail = [&](int start) -> vector<char> {
        vector<char> out_rev;
        vector<pair<int,char>> st;
        st.reserve(256);
        st.push_back({start, 0});
        while (!st.empty()) {
            int v = st.back().first;
            if (!adj[v].empty()) {
                Edge e = adj[v].back();
                adj[v].pop_back();
                st.push_back({e.to, e.ch});
            } else {
                char ch = st.back().second;
                st.pop_back();
                if (ch) out_rev.push_back(ch);
            }
        }
        reverse(out_rev.begin(), out_rev.end());
        return out_rev;
    };

    struct Trail { int start; vector<char> chars; };
    vector<Trail> trails;
    trails.reserve(M);

    for (int i = 0; i < V; i++) {
        if (!adj[i].empty()) {
            Trail tr;
            tr.start = i;
            tr.chars = build_trail(i);
            trails.push_back(std::move(tr));
        }
    }

    string S;
    S.reserve(4 * (int)trails.size() + M);
    for (auto &tr : trails) {
        S += decode4(tr.start);
        for (char c : tr.chars) S.push_back(c);
    }

    int ci = si, cj = sj;
    ostringstream oss;
    for (char c : S) {
        int idx = c - 'A';
        auto &v = pos[idx];
        int best_i = v[0].first, best_j = v[0].second;
        int best_d = abs(best_i - ci) + abs(best_j - cj);
        for (auto [i, j] : v) {
            int d = abs(i - ci) + abs(j - cj);
            if (d < best_d) {
                best_d = d;
                best_i = i;
                best_j = j;
            }
        }
        oss << best_i << ' ' << best_j << '\n';
        ci = best_i; cj = best_j;
    }

    cout << oss.str();
    return 0;
}