#include <bits/stdc++.h>
using namespace std;

const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};
const char dir_char[4] = {'U', 'D', 'L', 'R'};

class DSU {
    vector<int> parent, rank, vcount, ecount;
public:
    DSU(int n) {
        parent.resize(n);
        rank.resize(n, 0);
        vcount.resize(n, 0);
        ecount.resize(n, 0);
        for (int i = 0; i < n; ++i) parent[i] = i;
    }
    void reset(int n) {
        for (int i = 0; i < n; ++i) {
            parent[i] = i;
            rank[i] = 0;
            vcount[i] = 0;
            ecount[i] = 0;
        }
    }
    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    }
    void unite(int x, int y) {
        int rx = find(x), ry = find(y);
        if (rx == ry) {
            ecount[rx]++;
            return;
        }
        if (rank[rx] < rank[ry]) {
            parent[rx] = ry;
            vcount[ry] += vcount[rx];
            ecount[ry] += ecount[rx] + 1;
        } else {
            parent[ry] = rx;
            vcount[rx] += vcount[ry];
            ecount[rx] += ecount[ry] + 1;
            if (rank[rx] == rank[ry]) rank[rx]++;
        }
    }
    void set_count(int x, int v, int e) {
        vcount[x] = v;
        ecount[x] = e;
    }
    int get_vcount(int x) { return vcount[find(x)]; }
    int get_ecount(int x) { return ecount[find(x)]; }
};

int compute_tree_size(const vector<vector<int>>& board, int N, DSU& dsu) {
    dsu.reset(N * N);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int idx = i * N + j;
            if (board[i][j] != 0) dsu.set_count(idx, 1, 0);
        }
    }
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N - 1; ++j) {
            if (board[i][j] != 0 && board[i][j + 1] != 0) {
                if ((board[i][j] & 4) && (board[i][j + 1] & 1))
                    dsu.unite(i * N + j, i * N + (j + 1));
            }
        }
    }
    for (int i = 0; i < N - 1; ++i) {
        for (int j = 0; j < N; ++j) {
            if (board[i][j] != 0 && board[i + 1][j] != 0) {
                if ((board[i][j] & 8) && (board[i + 1][j] & 2))
                    dsu.unite(i * N + j, (i + 1) * N + j);
            }
        }
    }
    vector<bool> visited(N * N, false);
    int max_tree = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (board[i][j] == 0) continue;
            int idx = i * N + j;
            int root = dsu.find(idx);
            if (visited[root]) continue;
            visited[root] = true;
            int v = dsu.get_vcount(idx);
            int e = dsu.get_ecount(idx);
            if (e == v - 1) max_tree = max(max_tree, v);
        }
    }
    return max_tree;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int N, T;
    cin >> N >> T;
    vector<string> input_board(N);
    for (int i = 0; i < N; ++i) cin >> input_board[i];
    
    vector<vector<int>> board(N, vector<int>(N));
    int empty_r = -1, empty_c = -1;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            char c = input_board[i][j];
            int val;
            if (c >= '0' && c <= '9') val = c - '0';
            else val = c - 'a' + 10;
            board[i][j] = val;
            if (val == 0) { empty_r = i; empty_c = j; }
        }
    }
    
    DSU dsu(N * N);
    int initial_score = compute_tree_size(board, N, dsu);
    int best_score = initial_score;
    vector<char> best_seq;
    
    vector<vector<int>> current_board = board;
    int current_score = initial_score;
    int cur_r = empty_r, cur_c = empty_c;
    vector<char> current_seq;
    
    random_device rd;
    mt19937 rng(rd());
    uniform_real_distribution<> rand01(0.0, 1.0);
    
    double temp_init = 1.0;
    double temp_final = 0.001;
    double temp = temp_init;
    double cooling = exp(log(temp_final / temp_init) / T);
    
    for (int step = 0; step < T; ++step) {
        vector<int> moves;
        for (int d = 0; d < 4; ++d) {
            int nr = cur_r + dx[d];
            int nc = cur_c + dy[d];
            if (nr >= 0 && nr < N && nc >= 0 && nc < N) moves.push_back(d);
        }
        if (moves.empty()) continue;
        uniform_int_distribution<> rand_move(0, moves.size() - 1);
        int d = moves[rand_move(rng)];
        int nr = cur_r + dx[d], nc = cur_c + dy[d];
        
        swap(current_board[cur_r][cur_c], current_board[nr][nc]);
        int new_score = compute_tree_size(current_board, N, dsu);
        
        bool accept = false;
        if (new_score > current_score) accept = true;
        else {
            double prob = exp((new_score - current_score) / temp);
            if (rand01(rng) < prob) accept = true;
        }
        
        if (accept) {
            current_score = new_score;
            cur_r = nr; cur_c = nc;
            current_seq.push_back(dir_char[d]);
            if (current_score > best_score) {
                best_score = current_score;
                best_seq = current_seq;
                if (best_score == N * N - 1) break;
            }
        } else {
            swap(current_board[cur_r][cur_c], current_board[nr][nc]);
        }
        temp *= cooling;
    }
    
    string ans(best_seq.begin(), best_seq.end());
    cout << ans << endl;
    
    return 0;
}