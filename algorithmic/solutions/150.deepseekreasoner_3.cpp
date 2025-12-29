#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cassert>
#include <cstring>
#include <set>
#include <queue>

using namespace std;

const int N = 20;

struct Placement {
    int sid;
    int dir; // 0 horizontal, 1 vertical
    int i, j; // start cell
    int len;
    vector<pair<int, int>> cells; // positions of each character (length = len)
    string s; // the string itself
    bool valid;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int M;
    cin >> N >> M;
    vector<string> strs(M);
    for (int i = 0; i < M; ++i) {
        cin >> strs[i];
    }

    // grid: 0 means unassigned (will become '.' later), otherwise char 'A'..'H'
    vector<vector<char>> grid(N, vector<char>(N, 0));

    // all placements
    vector<Placement> placements;
    placements.reserve(M * 2 * N * N);

    // for each string, list of placement indices
    vector<vector<int>> string_placements(M);

    // for each cell, list of (placement index, offset in that placement)
    vector<vector<vector<pair<int, int>>>> cell_placements(N, vector<vector<pair<int, int>>>(N));

    // create all placements
    for (int sid = 0; sid < M; ++sid) {
        const string& s = strs[sid];
        int len = s.size();
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                // horizontal
                Placement ph;
                ph.sid = sid;
                ph.dir = 0;
                ph.i = i;
                ph.j = j;
                ph.len = len;
                ph.s = s;
                ph.cells.resize(len);
                for (int p = 0; p < len; ++p) {
                    int ci = i;
                    int cj = (j + p) % N;
                    ph.cells[p] = {ci, cj};
                }
                ph.valid = true;
                placements.push_back(ph);
                int pid_h = placements.size() - 1;
                string_placements[sid].push_back(pid_h);
                for (int p = 0; p < len; ++p) {
                    int ci = ph.cells[p].first;
                    int cj = ph.cells[p].second;
                    cell_placements[ci][cj].push_back({pid_h, p});
                }

                // vertical
                Placement pv;
                pv.sid = sid;
                pv.dir = 1;
                pv.i = i;
                pv.j = j;
                pv.len = len;
                pv.s = s;
                pv.cells.resize(len);
                for (int p = 0; p < len; ++p) {
                    int ci = (i + p) % N;
                    int cj = j;
                    pv.cells[p] = {ci, cj};
                }
                pv.valid = true;
                placements.push_back(pv);
                int pid_v = placements.size() - 1;
                string_placements[sid].push_back(pid_v);
                for (int p = 0; p < len; ++p) {
                    int ci = pv.cells[p].first;
                    int cj = pv.cells[p].second;
                    cell_placements[ci][cj].push_back({pid_v, p});
                }
            }
        }
    }

    // valid_count for each string
    vector<int> valid_count(M, 2 * N * N);
    vector<bool> satisfied(M, false);
    vector<int> chosen_placement(M, -1);

    // main greedy loop
    while (true) {
        // find string with smallest positive valid_count that is not yet satisfied
        int best_sid = -1;
        int min_count = 1e9;
        for (int sid = 0; sid < M; ++sid) {
            if (!satisfied[sid] && valid_count[sid] > 0 && valid_count[sid] < min_count) {
                min_count = valid_count[sid];
                best_sid = sid;
            }
        }
        if (best_sid == -1) break;

        // among valid placements of best_sid, choose one with fewest new cell assignments
        int best_pid = -1;
        int best_new_assign = 1e9;
        for (int pid : string_placements[best_sid]) {
            Placement& pl = placements[pid];
            if (!pl.valid) continue;
            int new_assign = 0;
            bool compat = true;
            for (int p = 0; p < pl.len; ++p) {
                int ci = pl.cells[p].first;
                int cj = pl.cells[p].second;
                char req = pl.s[p];
                if (grid[ci][cj] != 0) {
                    if (grid[ci][cj] != req) {
                        compat = false;
                        break;
                    }
                } else {
                    ++new_assign;
                }
            }
            if (!compat) continue;
            if (new_assign < best_new_assign) {
                best_new_assign = new_assign;
                best_pid = pid;
                if (best_new_assign == 0) break; // cannot be better
            }
        }

        if (best_pid == -1) {
            // should not happen, but for safety mark as unsatisfiable
            valid_count[best_sid] = 0;
            continue;
        }

        // commit to this placement
        Placement& pl = placements[best_pid];
        for (int p = 0; p < pl.len; ++p) {
            int ci = pl.cells[p].first;
            int cj = pl.cells[p].second;
            char req = pl.s[p];
            if (grid[ci][cj] == 0) {
                grid[ci][cj] = req;
                // invalidate conflicting placements that use this cell
                for (auto& [pid2, offset] : cell_placements[ci][cj]) {
                    Placement& pl2 = placements[pid2];
                    if (!pl2.valid) continue;
                    if (pl2.s[offset] != req) {
                        pl2.valid = false;
                        --valid_count[pl2.sid];
                    }
                }
            } else {
                // already assigned, must match
                assert(grid[ci][cj] == req);
            }
        }
        satisfied[best_sid] = true;
        chosen_placement[best_sid] = best_pid;
    }

    // mark cells that are necessary (used by chosen placements)
    vector<vector<bool>> necessary(N, vector<bool>(N, false));
    for (int sid = 0; sid < M; ++sid) {
        if (satisfied[sid]) {
            Placement& pl = placements[chosen_placement[sid]];
            for (int p = 0; p < pl.len; ++p) {
                int ci = pl.cells[p].first;
                int cj = pl.cells[p].second;
                necessary[ci][cj] = true;
            }
        }
    }

    // set non-necessary assigned cells back to unassigned (will become '.')
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != 0 && !necessary[i][j]) {
                grid[i][j] = 0;
            }
        }
    }

    // output
    for (int i = 0; i < N; ++i) {
        string row;
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] == 0) row += '.';
            else row += grid[i][j];
        }
        cout << row << '\n';
    }

    return 0;
}