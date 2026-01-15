#include <bits/stdc++.h>
using namespace std;

struct Device {
    long long id;
    int x, y;
    char type; // 'R' or 'S' or 'C'
};

static inline long long w_between(const Device& a, const Device& b) {
    long long dx = (long long)a.x - (long long)b.x;
    long long dy = (long long)a.y - (long long)b.y;
    long long D = dx*dx + dy*dy;
    int factor = ((a.type=='S') || (b.type=='S')) ? 4 : 5; // 0.8 -> 4, 1.0 -> 5
    return D * (long long)factor;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) {
        return 0;
    }
    vector<Device> robots;
    robots.reserve(N);
    for (int i = 0; i < N + K; ++i) {
        long long id;
        int x, y;
        string t;
        cin >> id >> x >> y >> t;
        char c = t.empty() ? 'R' : t[0];
        if (c != 'C') {
            Device d{ id, x, y, c };
            robots.push_back(d);
        }
    }

    int n = (int)robots.size();
    // Output selected relay stations (none)
    cout << "#\n";

    if (n <= 1) {
        cout << "\n";
        return 0;
    }

    const long long INF = (std::numeric_limits<long long>::max() / 4);
    vector<long long> key(n, INF);
    vector<int> parent(n, -1);
    vector<char> used(n, 0);

    key[0] = 0;

    for (int it = 0; it < n; ++it) {
        int u = -1;
        long long best = INF;
        for (int i = 0; i < n; ++i) {
            if (!used[i] && key[i] < best) {
                best = key[i];
                u = i;
            }
        }
        if (u == -1) break;
        used[u] = 1;

        for (int v = 0; v < n; ++v) {
            if (!used[v]) {
                long long w = w_between(robots[u], robots[v]);
                if (w < key[v]) {
                    key[v] = w;
                    parent[v] = u;
                }
            }
        }
    }

    // Output edges as "id1-id2" separated by '#'
    bool first = true;
    for (int i = 0; i < n; ++i) {
        if (parent[i] != -1) {
            if (!first) cout << "#";
            first = false;
            cout << robots[i].id << "-" << robots[parent[i]].id;
        }
    }
    cout << "\n";

    return 0;
}