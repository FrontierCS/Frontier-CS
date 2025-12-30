#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <map>

// Constants are fixed in the problem statement
const int N_GRID = 15;
const int M_WORDS = 200;
const int T_LEN = 5;

// Global variables for problem data
int start_r, start_c;
char grid[N_GRID][N_GRID];
std::vector<std::string> t_words(M_WORDS);
std::vector<std::pair<int, int>> char_positions[26];
int overlaps[M_WORDS][M_WORDS];

struct TypingResult {
    int cost = 1e9;
    std::vector<std::pair<int, int>> coords;
    std::pair<int, int> end_pos;
};

int manhattan_distance(std::pair<int, int> p1, std::pair<int, int> p2) {
    return std::abs(p1.first - p2.first) + std::abs(p1.second - p2.second);
}

TypingResult min_cost_to_type(const std::string& s, std::pair<int, int> start_pos) {
    if (s.empty()) {
        return {0, {}, start_pos};
    }

    int len = s.length();
    std::vector<std::vector<int>> dp(len);
    std::vector<std::vector<int>> parent(len);

    int first_char_code = s[0] - 'A';
    dp[0].resize(char_positions[first_char_code].size());
    for (size_t i = 0; i < char_positions[first_char_code].size(); ++i) {
        dp[0][i] = manhattan_distance(start_pos, char_positions[first_char_code][i]) + 1;
    }

    for (int k = 1; k < len; ++k) {
        int char_code = s[k] - 'A';
        int prev_char_code = s[k - 1] - 'A';
        dp[k].resize(char_positions[char_code].size());
        parent[k].resize(char_positions[char_code].size());

        for (size_t i = 0; i < char_positions[char_code].size(); ++i) {
            auto current_p = char_positions[char_code][i];
            int min_c = 1e9;
            int best_p_idx = -1;
            for (size_t j = 0; j < char_positions[prev_char_code].size(); ++j) {
                auto prev_p = char_positions[prev_char_code][j];
                int current_c = dp[k - 1][j] + manhattan_distance(prev_p, current_p) + 1;
                if (current_c < min_c) {
                    min_c = current_c;
                    best_p_idx = j;
                }
            }
            dp[k][i] = min_c;
            parent[k][i] = best_p_idx;
        }
    }

    int min_total_cost = 1e9;
    int end_idx = -1;
    int last_char_code = s[len - 1] - 'A';
    for (size_t i = 0; i < char_positions[last_char_code].size(); ++i) {
        if (dp[len - 1][i] < min_total_cost) {
            min_total_cost = dp[len - 1][i];
            end_idx = i;
        }
    }

    TypingResult result;
    result.cost = min_total_cost;
    result.end_pos = char_positions[last_char_code][end_idx];
    result.coords.resize(len);

    int current_idx = end_idx;
    for (int k = len - 1; k >= 0; --k) {
        int char_code = s[k] - 'A';
        result.coords[k] = char_positions[char_code][current_idx];
        if (k > 0) {
            current_idx = parent[k][current_idx];
        }
    }
    return result;
}

void solve() {
    std::cin >> start_r >> start_c;
    for (int i = 0; i < N_GRID; ++i) {
        for (int j = 0; j < N_GRID; ++j) {
            std::cin >> grid[i][j];
            char_positions[grid[i][j] - 'A'].push_back({i, j});
        }
    }
    for (int i = 0; i < M_WORDS; ++i) {
        std::cin >> t_words[i];
    }

    for (int i = 0; i < M_WORDS; ++i) {
        for (int j = 0; j < M_WORDS; ++j) {
            if (i == j) continue;
            for (int k = T_LEN - 1; k >= 1; --k) {
                if (t_words[i].substr(T_LEN - k) == t_words[j].substr(0, k)) {
                    overlaps[i][j] = k;
                    break;
                }
            }
        }
    }

    std::vector<std::pair<int, int>> start_candidates;
    for (int i = 0; i < M_WORDS; ++i) {
        start_candidates.push_back({min_cost_to_type(t_words[i], {start_r, start_c}).cost, i});
    }
    std::sort(start_candidates.begin(), start_candidates.end());

    int K = std::min(M_WORDS, 20);
    TypingResult best_overall_result;

    for (int i = 0; i < K; ++i) {
        int start_idx = start_candidates[i].second;

        std::vector<int> path;
        path.push_back(start_idx);
        std::vector<bool> visited(M_WORDS, false);
        visited[start_idx] = true;

        TypingResult current_run_result = min_cost_to_type(t_words[start_idx], {start_r, start_c});
        std::pair<int, int> current_pos = current_run_result.end_pos;

        for (int step = 1; step < M_WORDS; ++step) {
            int last_idx = path.back();
            int best_next_idx = -1;
            int best_k = -1;
            TypingResult best_suffix_result;

            for (int j = 0; j < M_WORDS; ++j) {
                if (!visited[j]) {
                    int k = overlaps[last_idx][j];
                    if (k > best_k) {
                        best_k = k;
                        std::string suffix = t_words[j].substr(k);
                        best_suffix_result = min_cost_to_type(suffix, current_pos);
                        best_next_idx = j;
                    } else if (k == best_k) {
                        std::string suffix = t_words[j].substr(k);
                        TypingResult res = min_cost_to_type(suffix, current_pos);
                        if (res.cost < best_suffix_result.cost) {
                            best_suffix_result = res;
                            best_next_idx = j;
                        }
                    }
                }
            }
            path.push_back(best_next_idx);
            visited[best_next_idx] = true;

            current_run_result.cost += best_suffix_result.cost;
            if (!best_suffix_result.coords.empty()) {
                current_run_result.coords.insert(current_run_result.coords.end(), best_suffix_result.coords.begin(), best_suffix_result.coords.end());
                current_pos = best_suffix_result.end_pos;
            }
        }
        
        if (current_run_result.cost < best_overall_result.cost) {
            best_overall_result = current_run_result;
        }
    }

    for (const auto& p : best_overall_result.coords) {
        std::cout << p.first << " " << p.second << '\n';
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n_dummy, m_dummy;
    std::cin >> n_dummy >> m_dummy;
    solve();
    return 0;
}