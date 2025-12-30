#include <bits/stdc++.h>
using namespace std;

int si, sj, ti, tj;
double p;
bool wall_right[20][19];
bool wall_down[19][20];
const string dirs = "UDLR";

// evaluate expected S for a given string
double evaluate(const string &s) {
    int L = s.size();
    double prob[20][20] = {0};
    prob[si][sj] = 1.0;
    vector<double> reach(L + 1, 0);
    for (int t = 1; t <= L; ++t) {
        char c = s[t - 1];
        int dir;
        if (c == 'U') dir = 0;
        else if (c == 'D') dir = 1;
        else if (c == 'L') dir = 2;
        else dir = 3; // 'R'
        double nprob[20][20] = {0};
        for (int i = 0; i < 20; ++i) {
            for (int j = 0; j < 20; ++j) {
                double cur = prob[i][j];
                if (cur == 0) continue;
                // forgetting
                nprob[i][j] += p * cur;
                // try to move
                int ni = i, nj = j;
                if (dir == 0) { // U
                    if (i > 0 && !wall_down[i - 1][j]) ni = i - 1;
                } else if (dir == 1) { // D
                    if (i < 19 && !wall_down[i][j]) ni = i + 1;
                } else if (dir == 2) { // L
                    if (j > 0 && !wall_right[i][j - 1]) nj = j - 1;
                } else { // R
                    if (j < 19 && !wall_right[i][j]) nj = j + 1;
                }
                if (ni == ti && nj == tj) {
                    reach[t] += (1 - p) * cur;
                } else {
                    nprob[ni][nj] += (1 - p) * cur;
                }
            }
        }
        memcpy(prob, nprob, sizeof(prob));
    }
    double score = 0;
    for (int t = 1; t <= L; ++t) {
        score += reach[t] * (401 - t);
    }
    return score;
}

// BFS to find a shortest path
string bfs() {
    int parent[20][20];
    char move[20][20];
    memset(parent, -1, sizeof(parent));
    queue<pair<int, int>> q;
    q.push({si, sj});
    parent[si][sj] = -2;
    while (!q.empty()) {
        auto [i, j] = q.front(); q.pop();
        if (i == ti && j == tj) break;
        // Up
        if (i > 0 && !wall_down[i - 1][j] && parent[i - 1][j] == -1) {
            parent[i - 1][j] = i * 20 + j;
            move[i - 1][j] = 'U';
            q.push({i - 1, j});
        }
        // Down
        if (i < 19 && !wall_down[i][j] && parent[i + 1][j] == -1) {
            parent[i + 1][j] = i * 20 + j;
            move[i + 1][j] = 'D';
            q.push({i + 1, j});
        }
        // Left
        if (j > 0 && !wall_right[i][j - 1] && parent[i][j - 1] == -1) {
            parent[i][j - 1] = i * 20 + j;
            move[i][j - 1] = 'L';
            q.push({i, j - 1});
        }
        // Right
        if (j < 19 && !wall_right[i][j] && parent[i][j + 1] == -1) {
            parent[i][j + 1] = i * 20 + j;
            move[i][j + 1] = 'R';
            q.push({i, j + 1});
        }
    }
    // reconstruct path
    string path;
    int i = ti, j = tj;
    while (parent[i][j] != -2) {
        char m = move[i][j];
        path.push_back(m);
        int par = parent[i][j];
        i = par / 20;
        j = par % 20;
    }
    reverse(path.begin(), path.end());
    return path;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // read input
    cin >> si >> sj >> ti >> tj >> p;
    for (int i = 0; i < 20; ++i) {
        string line;
        cin >> line;
        for (int j = 0; j < 19; ++j) {
            wall_right[i][j] = (line[j] == '1');
        }
    }
    for (int i = 0; i < 19; ++i) {
        string line;
        cin >> line;
        for (int j = 0; j < 20; ++j) {
            wall_down[i][j] = (line[j] == '1');
        }
    }

    // initial solution: shortest path with repetitions
    string shortest = bfs();
    string best_str = shortest;
    double best_score = evaluate(best_str);
    for (int r = 2; r <= 10; ++r) {
        string cand;
        cand.reserve(shortest.size() * r);
        for (char c : shortest) {
            for (int k = 0; k < r; ++k) cand.push_back(c);
        }
        if (cand.size() > 200) break;
        double sc = evaluate(cand);
        if (sc > best_score) {
            best_score = sc;
            best_str = cand;
        }
    }

    // local search
    string current = best_str;
    double current_score = best_score;
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> uniform(0.0, 1.0);
    uniform_int_distribution<int> rand_dir(0, 3);
    const int ITER = 2000;
    double start_temp = 1.0;
    double end_temp = 0.01;
    double decay = exp(log(end_temp / start_temp) / ITER);
    double temp = start_temp;

    for (int iter = 0; iter < ITER; ++iter) {
        string new_s = current;
        int type = rng() % 4;
        if (type == 0) { // change
            if (new_s.empty()) continue;
            int idx = rng() % new_s.size();
            char new_c = dirs[rand_dir(rng)];
            new_s[idx] = new_c;
        } else if (type == 1) { // insert
            if (new_s.size() >= 200) continue;
            int idx = rng() % (new_s.size() + 1);
            char new_c = dirs[rand_dir(rng)];
            new_s.insert(idx, 1, new_c);
        } else if (type == 2) { // delete
            if (new_s.size() <= 1) continue;
            int idx = rng() % new_s.size();
            new_s.erase(idx, 1);
        } else { // swap adjacent
            if (new_s.size() < 2) continue;
            int idx = rng() % (new_s.size() - 1);
            swap(new_s[idx], new_s[idx + 1]);
        }

        double new_score = evaluate(new_s);
        double delta = new_score - current_score;
        if (delta > 0 || uniform(rng) < exp(delta / temp)) {
            current = new_s;
            current_score = new_score;
            if (current_score > best_score) {
                best_score = current_score;
                best_str = current;
            }
        }
        temp *= decay;
    }

    cout << best_str << endl;
    return 0;
}