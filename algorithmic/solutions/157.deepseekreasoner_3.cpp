#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <random>
#include <chrono>
#include <algorithm>
using namespace std;

const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};
const int cur_bit[4] = {2, 8, 1, 4};
const int nb_bit[4] = {8, 2, 4, 1};

int computeTreeSize(const vector<vector<int>>& board) {
    int N = board.size();
    vector<vector<bool>> visited(N, vector<bool>(N, false));
    int best = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (board[i][j] != 0 && !visited[i][j]) {
                vector<pair<int,int>> stack;
                stack.push_back({i, j});
                visited[i][j] = true;
                int vertices = 0;
                int total_deg = 0;
                while (!stack.empty()) {
                    pair<int,int> p = stack.back();
                    stack.pop_back();
                    int x = p.first, y = p.second;
                    vertices++;
                    int deg = 0;
                    for (int d = 0; d < 4; ++d) {
                        int nx = x + dx[d];
                        int ny = y + dy[d];
                        if (nx < 0 || nx >= N || ny < 0 || ny >= N) continue;
                        if ((board[x][y] & cur_bit[d]) && (board[nx][ny] & nb_bit[d])) {
                            deg++;
                            if (!visited[nx][ny] && board[nx][ny] != 0) {
                                visited[nx][ny] = true;
                                stack.push_back({nx, ny});
                            }
                        }
                    }
                    total_deg += deg;
                }
                if (total_deg == 2 * (vertices - 1)) {
                    best = max(best, vertices);
                }
            }
        }
    }
    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, T;
    cin >> N >> T;
    vector<vector<int>> board(N, vector<int>(N));
    int ex = -1, ey = -1;
    for (int i = 0; i < N; ++i) {
        string s;
        cin >> s;
        for (int j = 0; j < N; ++j) {
            char c = s[j];
            int val;
            if (c >= '0' && c <= '9') val = c - '0';
            else val = 10 + (c - 'a');
            board[i][j] = val;
            if (val == 0) {
                ex = i;
                ey = j;
            }
        }
    }

    double temp_start = 10.0;
    double temp_end = 0.01;
    double cooling_factor = exp((log(temp_end) - log(temp_start)) / T);
    double temp = temp_start;

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> uniform(0.0, 1.0);

    int currentS = computeTreeSize(board);
    string moves;
    moves.reserve(T);

    for (int step = 0; step < T; ++step) {
        if (currentS == N * N - 1) break;

        vector<double> weights(4, 0.0);
        vector<int> legal_dirs;
        for (int d = 0; d < 4; ++d) {
            int nx = ex + dx[d];
            int ny = ey + dy[d];
            if (nx < 0 || nx >= N || ny < 0 || ny >= N) continue;
            // simulate move
            swap(board[ex][ey], board[nx][ny]);
            int newS = computeTreeSize(board);
            swap(board[ex][ey], board[nx][ny]);

            double delta = newS - currentS;
            double w = exp(delta / temp);
            weights[d] = w;
            legal_dirs.push_back(d);
        }

        if (legal_dirs.empty()) break;

        double total_weight = 0.0;
        for (int d : legal_dirs) total_weight += weights[d];
        double r = uniform(rng) * total_weight;
        double cum = 0.0;
        int chosen_d = -1;
        for (int d : legal_dirs) {
            cum += weights[d];
            if (r <= cum) {
                chosen_d = d;
                break;
            }
        }
        if (chosen_d == -1) chosen_d = legal_dirs.back();

        // perform move
        int nx = ex + dx[chosen_d];
        int ny = ey + dy[chosen_d];
        swap(board[ex][ey], board[nx][ny]);
        ex = nx;
        ey = ny;
        currentS = computeTreeSize(board);
        moves.push_back("UDLR"[chosen_d]);

        temp *= cooling_factor;
    }

    cout << moves << endl;
    return 0;
}