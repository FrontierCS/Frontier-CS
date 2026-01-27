#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <unordered_set>
#include <set>
#include <climits>

using namespace std;

struct State {
    int i, j, dir;
    bool operator<(const State& other) const {
        if (i != other.i) return i < other.i;
        if (j != other.j) return j < other.j;
        return dir < other.dir;
    }
};

int r, c;
vector<string> grid;
vector<vector<vector<int>>> dist;
const int di[4] = {-1, 0, 1, 0};
const int dj[4] = {0, 1, 0, -1};

void precompute_dist() {
    dist.assign(r, vector<vector<int>>(c, vector<int>(4, -1));
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] != '.') continue;
            for (int d = 0; d < 4; ++d) {
                int ni = i + di[d];
                int nj = j + dj[d];
                int cnt = 0;
                while (ni >= 0 && ni < r && nj >= 0 && nj < c && grid[ni][nj] == '.') {
                    ++cnt;
                    ni += di[d];
                    nj += dj[d];
                }
                dist[i][j][d] = cnt;
            }
        }
    }
}

size_t compute_hash(const vector<State>& states) {
    vector<int> ids;
    for (const State& s : states) {
        ids.push_back((s.i * c + s.j) * 4 + s.dir);
    }
    sort(ids.begin(), ids.end());
    size_t h = 0;
    const size_t prime = 1000000007;
    for (int id : ids) {
        h = h * prime + id;
    }
    return h;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> r >> c;
    grid.resize(r);
    for (int i = 0; i < r; ++i) {
        cin >> grid[i];
    }

    precompute_dist();

    // Initial set: all open cells, all directions
    vector<State> S;
    for (int i = 0; i < r; ++i) {
        for (int j = 0; j < c; ++j) {
            if (grid[i][j] == '.') {
                for (int d = 0; d < 4; ++d) {
                    S.push_back({i, j, d});
                }
            }
        }
    }

    unordered_set<size_t> seen_states;
    int d;
    cin >> d; // first distance reading

    while (true) {
        // Filter S by current observation
        vector<State> S_new;
        for (const State& s : S) {
            if (dist[s.i][s.j][s.dir] == d) {
                S_new.push_back(s);
            }
        }
        S.swap(S_new);

        if (S.empty()) {
            cout << "no" << endl;
            break;
        }
        if (S.size() == 1) {
            State s = S[0];
            cout << "yes " << s.i+1 << " " << s.j+1 << endl;
            break;
        }

        size_t h = compute_hash(S);
        if (seen_states.count(h)) {
            // We have been in this exact set before -> cycle
            cout << "no" << endl;
            break;
        }
        seen_states.insert(h);

        // Evaluate possible actions
        vector<string> actions = {"left", "right", "step"};
        int best_worst = INT_MAX;
        string best_action;

        for (const string& act : actions) {
            if (act == "step") {
                bool safe = true;
                for (const State& s : S) {
                    int ni = s.i + di[s.dir];
                    int nj = s.j + dj[s.dir];
                    if (ni < 0 || ni >= r || nj < 0 || nj >= c || grid[ni][nj] != '.') {
                        safe = false;
                        break;
                    }
                }
                if (!safe) continue;
            }

            // Compute distinct resulting states and group by distance
            set<State> S_prime_set;
            for (const State& s : S) {
                State ns = s;
                if (act == "left") {
                    ns.dir = (s.dir + 3) % 4;
                } else if (act == "right") {
                    ns.dir = (s.dir + 1) % 4;
                } else { // step
                    ns.i = s.i + di[s.dir];
                    ns.j = s.j + dj[s.dir];
                }
                S_prime_set.insert(ns);
            }

            unordered_map<int, int> group_sizes;
            for (const State& ns : S_prime_set) {
                int nd = dist[ns.i][ns.j][ns.dir];
                group_sizes[nd]++;
            }

            int worst = 0;
            for (const auto& p : group_sizes) {
                worst = max(worst, p.second);
            }
            if (worst < best_worst) {
                best_worst = worst;
                best_action = act;
            }
        }

        cout << best_action << endl;

        // Update S to the set after taking best_action
        set<State> S_next_set;
        for (const State& s : S) {
            State ns = s;
            if (best_action == "left") {
                ns.dir = (s.dir + 3) % 4;
            } else if (best_action == "right") {
                ns.dir = (s.dir + 1) % 4;
            } else { // step
                ns.i = s.i + di[s.dir];
                ns.j = s.j + dj[s.dir];
            }
            S_next_set.insert(ns);
        }
        S.assign(S_next_set.begin(), S_next_set.end());

        // Read next distance
        cin >> d;
        if (d == -1) break; // should not normally happen
    }

    return 0;
}