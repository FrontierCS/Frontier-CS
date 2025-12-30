#include <bits/stdc++.h>
using namespace std;

const int N = 30;
const int TOTAL_PORTS = N * N * 4;
int di[4] = {0, -1, 0, 1};
int dj[4] = {-1, 0, 1, 0};

int to[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1}
};

int rotated_type(int t, int r) {
    if (t <= 3) {
        return (t + r) & 3;
    } else if (t <= 5) {
        if (r & 1) return t ^ 1;
        else return t;
    } else {
        if (r & 1) return t ^ 1;
        else return t;
    }
}

int t[N][N];
int rot[N][N];
bool active[TOTAL_PORTS];
int internal[TOTAL_PORTS];
int external[TOTAL_PORTS];
bool vis[TOTAL_PORTS];

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

inline int get_port_id(int i, int j, int d) {
    return (i * N + j) * 4 + d;
}

long long compute_score() {
    memset(active, 0, sizeof(active));
    memset(internal, -1, sizeof(internal));
    memset(external, -1, sizeof(external));

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            int eff = rotated_type(t[i][j], rot[i][j]);
            int base = (i * N + j) * 4;
            for (int d = 0; d < 4; d++) {
                int id = base + d;
                if (to[eff][d] != -1) {
                    active[id] = true;
                    internal[id] = base + to[eff][d];
                }
            }
        }
    }

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            for (int d = 0; d < 4; d++) {
                int id = get_port_id(i, j, d);
                if (!active[id]) continue;
                int ni = i + di[d];
                int nj = j + dj[d];
                if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
                int nd = (d + 2) % 4;
                int nid = get_port_id(ni, nj, nd);
                if (active[nid]) {
                    external[id] = nid;
                }
            }
        }
    }

    memset(vis, 0, sizeof(vis));
    long long max1 = 0, max2 = 0;

    for (int id = 0; id < TOTAL_PORTS; id++) {
        if (!active[id] || vis[id]) continue;
        int deg = (internal[id] != -1) + (external[id] != -1);
        if (deg != 2) {
            vector<int> stack;
            stack.push_back(id);
            while (!stack.empty()) {
                int cur = stack.back();
                stack.pop_back();
                if (vis[cur]) continue;
                vis[cur] = true;
                if (internal[cur] != -1 && !vis[internal[cur]]) stack.push_back(internal[cur]);
                if (external[cur] != -1 && !vis[external[cur]]) stack.push_back(external[cur]);
            }
        }
    }

    for (int id = 0; id < TOTAL_PORTS; id++) {
        if (!active[id] || vis[id]) continue;
        int start = id;
        int cur = start;
        int prev = -1;
        int length = 0;
        do {
            vis[cur] = true;
            int next = -1;
            if (internal[cur] != -1 && internal[cur] != prev) next = internal[cur];
            else if (external[cur] != -1 && external[cur] != prev) next = external[cur];
            if (external[cur] == next) length++;
            prev = cur;
            cur = next;
        } while (cur != start);
        if (length > max1) {
            max2 = max1;
            max1 = length;
        } else if (length > max2) {
            max2 = length;
        }
    }

    return max1 * max2;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    for (int i = 0; i < N; i++) {
        string s;
        cin >> s;
        for (int j = 0; j < N; j++) {
            t[i][j] = s[j] - '0';
        }
    }

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            rot[i][j] = rng() & 3;
        }
    }

    long long current_score = compute_score();
    int max_iter = 2000;
    double T = 500.0;
    double decay = 0.995;

    for (int iter = 0; iter < max_iter; iter++) {
        int i = rng() % N;
        int j = rng() % N;
        int old_rot = rot[i][j];
        int new_rot;
        do {
            new_rot = rng() & 3;
        } while (new_rot == old_rot);

        rot[i][j] = new_rot;
        long long new_score = compute_score();
        long long delta = new_score - current_score;
        if (delta > 0 || (double)rng() / mt19937::max() < exp(delta / T)) {
            current_score = new_score;
        } else {
            rot[i][j] = old_rot;
        }
        T *= decay;
    }

    string ans;
    ans.reserve(N * N);
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            ans.push_back('0' + rot[i][j]);
        }
    }
    cout << ans << endl;

    return 0;
}