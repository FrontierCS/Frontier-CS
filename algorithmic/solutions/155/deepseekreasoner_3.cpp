#include <iostream>
#include <vector>
#include <queue>
#include <string>
#include <algorithm>
#include <random>
#include <cmath>
#include <cstring>

using namespace std;

const int N = 20;
const int CELLS = 400;

int next_cell[4][CELLS]; // 0:U,1:D,2:L,3:R

int char_to_dir(char c) {
    if (c == 'U') return 0;
    if (c == 'D') return 1;
    if (c == 'L') return 2;
    return 3;
}

string bfs(int start, int target) {
    vector<int> parent(CELLS, -1);
    vector<char> dir_char(CELLS);
    queue<int> q;
    parent[start] = start;
    q.push(start);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        if (u == target) break;
        for (int d = 0; d < 4; ++d) {
            int v = next_cell[d][u];
            if (v == u) continue; // wall
            if (parent[v] == -1) {
                parent[v] = u;
                dir_char[v] = "UDLR"[d];
                q.push(v);
            }
        }
    }
    string path;
    int u = target;
    while (u != start) {
        path += dir_char[u];
        u = parent[u];
    }
    reverse(path.begin(), path.end());
    return path;
}

double compute_score(const string& moves, int start, int target, double p,
                     vector<double>& prob, vector<double>& new_prob) {
    int L = moves.size();
    fill(prob.begin(), prob.end(), 0.0);
    prob[start] = 1.0;
    double expected = 0.0;
    for (int k = 0; k < L; ++k) {
        int dir = char_to_dir(moves[k]);
        fill(new_prob.begin(), new_prob.end(), 0.0);
        for (int cell = 0; cell < CELLS; ++cell) {
            double f = prob[cell];
            if (f == 0.0) continue;
            new_prob[cell] += p * f;
            int next = next_cell[dir][cell];
            new_prob[next] += (1 - p) * f;
        }
        double reached = new_prob[target];
        if (reached > 0) {
            expected += reached * (401 - (k + 1));
            new_prob[target] = 0;
        }
        prob.swap(new_prob);
    }
    return expected;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj, ti, tj;
    double p;
    cin >> si >> sj >> ti >> tj >> p;
    vector<string> h(N), v(N - 1);
    for (int i = 0; i < N; ++i) cin >> h[i];
    for (int i = 0; i < N - 1; ++i) cin >> v[i];

    // Precompute next_cell
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int id = i * N + j;
            // Up
            if (i > 0 && v[i - 1][j] == '0')
                next_cell[0][id] = (i - 1) * N + j;
            else
                next_cell[0][id] = id;
            // Down
            if (i < N - 1 && v[i][j] == '0')
                next_cell[1][id] = (i + 1) * N + j;
            else
                next_cell[1][id] = id;
            // Left
            if (j > 0 && h[i][j - 1] == '0')
                next_cell[2][id] = i * N + (j - 1);
            else
                next_cell[2][id] = id;
            // Right
            if (j < N - 1 && h[i][j] == '0')
                next_cell[3][id] = i * N + (j + 1);
            else
                next_cell[3][id] = id;
        }
    }

    int start = si * N + sj;
    int target = ti * N + tj;

    // Shortest path
    string shortest = bfs(start, target);
    int d = shortest.size();

    // Determine repetition factor based on p
    int r = 1;
    if (p > 0.4) r = 5;
    else if (p > 0.3) r = 4;
    else if (p > 0.2) r = 3;
    else if (p > 0.15) r = 2;
    // Ensure total length <= 200
    r = min(r, 200 / max(d, 1));
    if (r < 1) r = 1;

    // Build initial string by repeating each move r times
    string init;
    for (char c : shortest) {
        for (int i = 0; i < r; ++i) init += c;
    }
    if (init.size() > 200) init.resize(200);

    // Workspace for compute_score
    vector<double> prob(CELLS), new_prob(CELLS);

    // Evaluate initial
    double best_score = compute_score(init, start, target, p, prob, new_prob);
    string best = init;

    // Simulated annealing
    string cur = best;
    double cur_score = best_score;
    int L = cur.size();

    mt19937 rng(random_device{}());
    uniform_real_distribution<> unif(0.0, 1.0);
    const int ITER = 500;
    double T = 1.0;
    const double COOL = 0.995;

    for (int iter = 0; iter < ITER; ++iter) {
        string cand = cur;
        int type = rng() % 3;
        bool valid = true;

        if (type == 0) { // change
            int idx = rng() % L;
            char newc = "UDLR"[rng() % 4];
            if (cand[idx] != newc) cand[idx] = newc;
        } else if (type == 1) { // insert
            if (L >= 200) { type = 0; continue; }
            int idx = rng() % (L + 1);
            char newc = "UDLR"[rng() % 4];
            cand.insert(idx, 1, newc);
        } else { // delete
            if (L <= 1) { type = 0; continue; }
            int idx = rng() % L;
            cand.erase(idx, 1);
        }

        double score = compute_score(cand, start, target, p, prob, new_prob);
        if (score > cur_score || exp((score - cur_score) / T) > unif(rng)) {
            cur = cand;
            cur_score = score;
            L = cur.size();
            if (score > best_score) {
                best = cand;
                best_score = score;
            }
        }
        T *= COOL;
    }

    cout << best << endl;
    return 0;
}