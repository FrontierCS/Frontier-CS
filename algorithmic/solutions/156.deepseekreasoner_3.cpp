#include <bits/stdc++.h>
using namespace std;

const int N = 30;
const int PORTS = N * N * 4;
const int MAX_ITER = 2000;
const double T_START = 1.0;
const double T_END = 0.001;
const double COOL = pow(T_END / T_START, 1.0 / MAX_ITER);

int tile_conn[8][4][4];   // [type][rotation][dir] -> partner dir or -1
int port_external[PORTS]; // precomputed external neighbor port id

// base connectivity for tile types 0..7 (rotation 0)
int base_to[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1}
};

inline int port_id(int i, int j, int d) {
    return (i * N + j) * 4 + d;
}

void precompute() {
    // compute base tile_conn from base_to
    int base_conn[8][4];
    for (int t = 0; t < 8; ++t) {
        for (int d = 0; d < 4; ++d) base_conn[t][d] = -1;
        for (int d = 0; d < 4; ++d) {
            int to = base_to[t][d];
            if (to != -1) {
                base_conn[t][d] = to;
                base_conn[t][to] = d;
            }
        }
        // for each rotation
        for (int r = 0; r < 4; ++r) {
            for (int d = 0; d < 4; ++d) {
                int rd = (d - r + 4) % 4; // rotate back
                int partner = base_conn[t][rd];
                if (partner == -1)
                    tile_conn[t][r][d] = -1;
                else
                    tile_conn[t][r][d] = (partner + r) % 4;
            }
        }
    }

    // precompute external neighbor for each port
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            for (int d = 0; d < 4; ++d) {
                int p = port_id(i, j, d);
                int ni = i, nj = j;
                if (d == 0) { // left
                    if (j == 0) { port_external[p] = -1; continue; }
                    nj = j - 1;
                    port_external[p] = port_id(ni, nj, 2); // right of left neighbor
                } else if (d == 1) { // up
                    if (i == 0) { port_external[p] = -1; continue; }
                    ni = i - 1;
                    port_external[p] = port_id(ni, nj, 3); // down of up neighbor
                } else if (d == 2) { // right
                    if (j == N - 1) { port_external[p] = -1; continue; }
                    nj = j + 1;
                    port_external[p] = port_id(ni, nj, 0); // left of right neighbor
                } else { // down
                    if (i == N - 1) { port_external[p] = -1; continue; }
                    ni = i + 1;
                    port_external[p] = port_id(ni, nj, 1); // up of down neighbor
                }
            }
        }
    }
}

struct State {
    int rotation[N][N];
    bool port_active[PORTS];
    int port_internal[PORTS];
    long long score;
};

long long compute_score(bool port_active[], int port_internal[]) {
    static int visited[PORTS];
    static int stamp = 0;
    ++stamp;
    vector<int> cycles;
    for (int p = 0; p < PORTS; ++p) {
        if (!port_active[p] || visited[p] == stamp) continue;
        // BFS/DFS to collect component
        vector<int> comp;
        stack<int> st;
        st.push(p);
        visited[p] = stamp;
        while (!st.empty()) {
            int x = st.top(); st.pop();
            comp.push_back(x);
            // internal neighbor
            int y = port_internal[x];
            if (y != -1 && visited[y] != stamp) {
                visited[y] = stamp;
                st.push(y);
            }
            // external neighbor (if both active)
            y = port_external[x];
            if (y != -1 && port_active[y] && visited[y] != stamp) {
                visited[y] = stamp;
                st.push(y);
            }
        }
        // check if component is a cycle
        int boundary = 0;
        for (int x : comp) {
            int deg = 0;
            if (port_active[x]) ++deg;
            int ext = port_external[x];
            if (ext != -1 && port_active[ext]) ++deg;
            if (deg < 2) ++boundary;
        }
        if (boundary == 0) {
            cycles.push_back(comp.size() / 2);
        }
    }
    if (cycles.size() < 2) return 0;
    sort(cycles.rbegin(), cycles.rend());
    return (long long)cycles[0] * cycles[1];
}

void update_tile(int i, int j, int rot, int tile_type,
                 bool port_active[], int port_internal[]) {
    int base = port_id(i, j, 0);
    // clear old connections (set inactive and internal -1 for the four ports)
    for (int d = 0; d < 4; ++d) {
        int p = base + d;
        port_active[p] = false;
        port_internal[p] = -1;
    }
    // set new connections according to tile_conn[tile_type][rot]
    for (int d = 0; d < 4; ++d) {
        int partner = tile_conn[tile_type][rot][d];
        if (partner != -1) {
            int p = base + d;
            int q = base + partner;
            port_active[p] = true;
            port_active[q] = true;
            port_internal[p] = q;
            port_internal[q] = p;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    precompute();

    // read input
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) {
        cin >> grid[i];
    }

    // random number generator
    random_device rd;
    mt19937 gen(rd());
    uniform_real_distribution<> dis(0.0, 1.0);
    uniform_int_distribution<> tile_dist(0, N-1);
    uniform_int_distribution<> rot_dist(0, 3);

    // initial state: all rotations 0
    State state;
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            state.rotation[i][j] = 0;

    // initialize port arrays
    fill(state.port_active, state.port_active + PORTS, false);
    fill(state.port_internal, state.port_internal + PORTS, -1);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int t = grid[i][j] - '0';
            update_tile(i, j, 0, t, state.port_active, state.port_internal);
        }
    }
    state.score = compute_score(state.port_active, state.port_internal);

    // simulated annealing
    double T = T_START;
    for (int iter = 0; iter < MAX_ITER; ++iter) {
        // pick random tile
        int i = tile_dist(gen);
        int j = tile_dist(gen);
        int old_rot = state.rotation[i][j];
        int new_rot;
        do {
            new_rot = rot_dist(gen);
        } while (new_rot == old_rot);

        int t = grid[i][j] - '0';

        // backup old port data for this tile (4 ports)
        int base = port_id(i, j, 0);
        bool old_active[4];
        int old_internal[4];
        for (int d = 0; d < 4; ++d) {
            int p = base + d;
            old_active[d] = state.port_active[p];
            old_internal[d] = state.port_internal[p];
        }

        // apply new rotation
        update_tile(i, j, new_rot, t, state.port_active, state.port_internal);
        long long new_score = compute_score(state.port_active, state.port_internal);

        long long diff = new_score - state.score;
        if (diff > 0 || exp(diff / T) > dis(gen)) {
            // accept
            state.score = new_score;
            state.rotation[i][j] = new_rot;
        } else {
            // revert
            for (int d = 0; d < 4; ++d) {
                int p = base + d;
                state.port_active[p] = old_active[d];
                state.port_internal[p] = old_internal[d];
            }
            // also need to restore symmetry: if a port had an internal partner,
            // that partner is within the same tile, so already restored.
        }
        T *= COOL;
    }

    // output rotations as a string of 900 digits
    string ans;
    ans.reserve(N * N);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            ans += char('0' + state.rotation[i][j]);
        }
    }
    cout << ans << endl;
    return 0;
}