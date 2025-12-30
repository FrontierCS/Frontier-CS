#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <random>
#include <algorithm>
#include <map>

using namespace std;

// Globals
int N, M;
vector<string> S;

// Randomness
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Timer
chrono::steady_clock::time_point start_time;

// Placement
struct Placement {
    int r, c, d; // 0 for horizontal, 1 for vertical
};
vector<Placement> placements;

// Precomputed correlations
vector<vector<vector<int>>> corr_hh, corr_vv;
vector<vector<vector<vector<int>>>> corr_hv, corr_vh;

inline int positive_modulo(int i, int n) {
    return (i % n + n) % n;
}

void precompute() {
    corr_hh.resize(M, vector<vector<int>>(M, vector<int>(N)));
    corr_vv.resize(M, vector<vector<int>>(M, vector<int>(N)));
    corr_hv.resize(M, vector<vector<vector<int>>>(M));
    corr_vh.resize(M, vector<vector<vector<int>>>(M));

    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            // HH
            for (int shift = 0; shift < N; ++shift) {
                int score = 0;
                for (int k = 0; k < S[i].length(); ++k) {
                    int l = k - shift;
                    if (l >= 0 && l < S[j].length()) {
                        score += (S[i][k] == S[j][l] ? 1 : -1);
                    }
                }
                corr_hh[i][j][shift] = score;
            }

            // VV
            for (int shift = 0; shift < N; ++shift) {
                int score = 0;
                for (int k = 0; k < S[i].length(); ++k) {
                    int l = k - shift;
                    if (l >= 0 && l < S[j].length()) {
                        score += (S[i][k] == S[j][l] ? 1 : -1);
                    }
                }
                corr_vv[i][j][shift] = score;
            }

            // HV
            corr_hv[i][j].resize(S[i].length(), vector<int>(S[j].length()));
            for (int k = 0; k < S[i].length(); ++k) {
                for (int l = 0; l < S[j].length(); ++l) {
                    corr_hv[i][j][k][l] = (S[i][k] == S[j][l] ? 1 : -1);
                }
            }

            // VH
            corr_vh[i][j].resize(S[i].length(), vector<int>(S[j].length()));
            for (int k = 0; k < S[i].length(); ++k) {
                for (int l = 0; l < S[j].length(); ++l) {
                    corr_vh[i][j][k][l] = (S[i][k] == S[j][l] ? 1 : -1);
                }
            }
        }
    }
}

Placement find_best_placement(int target_idx, const vector<int>& placed_indices) {
    long long best_score = -2e18;
    Placement best_p = {-1, -1, -1};

    for (int d = 0; d < 2; ++d) {
        vector<vector<long long>> score_grid(N, vector<long long>(N, 0));
        for (int prev_idx : placed_indices) {
            if (prev_idx == target_idx) continue;
            const auto& prev_p = placements[prev_idx];

            if (d == 0) { // target horizontal
                if (prev_p.d == 0) { // prev horizontal
                    for (int shift = 0; shift < N; ++shift) {
                        score_grid[prev_p.r][positive_modulo(prev_p.c + shift, N)] += corr_hh[target_idx][prev_idx][shift];
                    }
                } else { // prev vertical
                    for (int k = 0; k < S[target_idx].length(); ++k) {
                        for (int l = 0; l < S[prev_idx].length(); ++l) {
                            int r = positive_modulo(prev_p.r + l, N);
                            int c = positive_modulo(prev_p.c - k, N);
                            score_grid[r][c] += corr_hv[target_idx][prev_idx][k][l];
                        }
                    }
                }
            } else { // target vertical
                if (prev_p.d == 0) { // prev horizontal
                    for (int k = 0; k < S[target_idx].length(); ++k) {
                        for (int l = 0; l < S[prev_idx].length(); ++l) {
                            int r = positive_modulo(prev_p.r - k, N);
                            int c = positive_modulo(prev_p.c + l, N);
                            score_grid[r][c] += corr_vh[target_idx][prev_idx][k][l];
                        }
                    }
                } else { // prev vertical
                    for (int shift = 0; shift < N; ++shift) {
                        score_grid[positive_modulo(prev_p.r + shift, N)][prev_p.c] += corr_vv[target_idx][prev_idx][shift];
                    }
                }
            }
        }

        for (int r = 0; r < N; ++r) {
            for (int c = 0; c < N; ++c) {
                if (score_grid[r][c] > best_score) {
                    best_score = score_grid[r][c];
                    best_p = {r, c, d};
                }
            }
        }
    }
    return best_p;
}

void greedy_construction() {
    vector<int> p(M);
    for(int i=0; i<M; ++i) p[i] = i;
    sort(p.begin(), p.end(), [&](int a, int b){
        if (S[a].length() != S[b].length()) {
            return S[a].length() > S[b].length();
        }
        return a < b;
    });

    vector<bool> placed_mask(M, false);
    vector<int> placed_indices;

    int first_idx = p[0];
    placements[first_idx] = {0, 0, 0}; // Start with horizontal
    placed_mask[first_idx] = true;
    placed_indices.push_back(first_idx);

    for (int i = 1; i < M; ++i) {
        int current_idx = p[i];
        placements[current_idx] = find_best_placement(current_idx, placed_indices);
        placed_mask[current_idx] = true;
        placed_indices.push_back(current_idx);
    }
}

void local_search() {
    vector<int> all_indices(M);
    for(int i=0; i<M; ++i) all_indices[i] = i;
    
    while (chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - start_time).count() < 2800) {
        int target_idx = rng() % M;
        placements[target_idx] = find_best_placement(target_idx, all_indices);
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    start_time = chrono::steady_clock::now();

    cin >> N >> M;
    S.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> S[i];
    }
    placements.resize(M);

    precompute();
    greedy_construction();
    local_search();
    
    vector<string> grid(N, string(N, '.'));
    vector<vector<map<char, int>>> votes(N, vector<map<char, int>>(N));
    
    for(int i=0; i<M; ++i) {
        const auto& p = placements[i];
        if (p.r == -1) continue;
        if (p.d == 0) { // Horizontal
            for(int k=0; k<S[i].length(); ++k) {
                votes[p.r][positive_modulo(p.c + k, N)][S[i][k]]++;
            }
        } else { // Vertical
            for(int k=0; k<S[i].length(); ++k) {
                votes[positive_modulo(p.r + k, N)][p.c][S[i][k]]++;
            }
        }
    }

    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (votes[r][c].empty()) {
                grid[r][c] = '.';
            } else {
                char best_char = '.';
                int max_vote = 0;
                bool tie = false;
                for (auto const& [key, val] : votes[r][c]) {
                    if (val > max_vote) {
                        max_vote = val;
                        best_char = key;
                        tie = false;
                    } else if (val == max_vote) {
                        tie = true;
                    }
                }
                if (tie) {
                    grid[r][c] = '.';
                } else {
                    grid[r][c] = best_char;
                }
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << grid[i] << endl;
    }

    return 0;
}