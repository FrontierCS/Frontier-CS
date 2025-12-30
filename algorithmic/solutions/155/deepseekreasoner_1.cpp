#include <bits/stdc++.h>
using namespace std;

const int L = 200;
const int BEAM_WIDTH = 100;
const int N = 20;

double p;
int si, sj, ti, tj;
bool wall_down[N][N];
bool wall_right[N][N];

bool can_go(int i, int j, char dir) {
    switch(dir) {
        case 'U': return i > 0 && !wall_down[i-1][j];
        case 'D': return i < N-1 && !wall_down[i][j];
        case 'L': return j > 0 && !wall_right[i][j-1];
        case 'R': return j < N-1 && !wall_right[i][j];
    }
    return false;
}

pair<int,int> get_next(int i, int j, char dir) {
    if (can_go(i, j, dir)) {
        switch(dir) {
            case 'U': return {i-1, j};
            case 'D': return {i+1, j};
            case 'L': return {i, j-1};
            case 'R': return {i, j+1};
        }
    }
    return {i, j};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    cin >> si >> sj >> ti >> tj >> p;
    for (int i = 0; i < N; ++i) {
        string s;
        cin >> s;
        for (int j = 0; j < N-1; ++j) {
            wall_right[i][j] = (s[j] == '1');
        }
    }
    for (int i = 0; i < N-1; ++i) {
        string s;
        cin >> s;
        for (int j = 0; j < N; ++j) {
            wall_down[i][j] = (s[j] == '1');
        }
    }
    
    vector<vector<vector<double>>> F(L+2, vector<vector<double>>(N, vector<double>(N, 0.0)));
    for (int step = L; step >= 1; --step) {
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (i == ti && j == tj) {
                    F[step][i][j] = 401 - step;
                    continue;
                }
                double best = 0.0;
                const string dirs = "URDL";
                for (char d : dirs) {
                    double val_forget = F[step+1][i][j];
                    auto [ni, nj] = get_next(i, j, d);
                    double val_move;
                    if (ni == ti && nj == tj) {
                        val_move = 401 - step;
                    } else {
                        val_move = F[step+1][ni][nj];
                    }
                    double val = p * val_forget + (1-p) * val_move;
                    if (val > best) best = val;
                }
                F[step][i][j] = best;
            }
        }
    }
    
    struct Candidate {
        string s;
        double accum;
        double prob[N][N];
        double total_est;
    };
    vector<Candidate> beam;
    Candidate init;
    init.s = "";
    init.accum = 0.0;
    memset(init.prob, 0, sizeof(init.prob));
    init.prob[si][sj] = 1.0;
    beam.push_back(init);
    
    for (int len = 0; len < L; ++len) {
        vector<Candidate> next_candidates;
        for (const Candidate& cand : beam) {
            for (char d : {'D','R','U','L'}) {
                Candidate new_cand;
                new_cand.s = cand.s + d;
                new_cand.accum = cand.accum;
                memset(new_cand.prob, 0, sizeof(new_cand.prob));
                double arr_contrib = 0.0;
                for (int i = 0; i < N; ++i) {
                    for (int j = 0; j < N; ++j) {
                        double P = cand.prob[i][j];
                        if (P == 0.0) continue;
                        new_cand.prob[i][j] += P * p;
                        auto [ni, nj] = get_next(i, j, d);
                        if (ni == ti && nj == tj) {
                            arr_contrib += P * (1-p) * (401 - (len+1));
                        } else {
                            new_cand.prob[ni][nj] += P * (1-p);
                        }
                    }
                }
                new_cand.accum += arr_contrib;
                double heuristic = 0.0;
                int next_step = len + 2;
                if (next_step <= L) {
                    for (int i = 0; i < N; ++i) {
                        for (int j = 0; j < N; ++j) {
                            if (new_cand.prob[i][j] > 0) {
                                heuristic += new_cand.prob[i][j] * F[next_step][i][j];
                            }
                        }
                    }
                }
                new_cand.total_est = new_cand.accum + heuristic;
                next_candidates.push_back(new_cand);
            }
        }
        sort(next_candidates.begin(), next_candidates.end(),
             [](const Candidate& a, const Candidate& b) {
                 return a.total_est > b.total_est;
             });
        if (next_candidates.size() > BEAM_WIDTH) {
            next_candidates.resize(BEAM_WIDTH);
        }
        beam = move(next_candidates);
    }
    
    Candidate best = beam[0];
    for (const Candidate& cand : beam) {
        if (cand.accum > best.accum) {
            best = cand;
        }
    }
    
    cout << best.s << endl;
    
    return 0;
}