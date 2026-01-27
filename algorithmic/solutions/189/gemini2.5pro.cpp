#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <unordered_map>
#include <chrono>
#include <random>
#include <set>
#include <string_view>

// Match structure for Maximal Exact Matches
struct Match {
    int i, j, len;
};

// Parameters
const int K_SEED = 12;
const int MIN_MEM_LEN = 12;
const int BAND_WIDTH = 50;
const int MAX_DP_SIZE = 250000; // Switch to full DP for small subproblems (e.g., 500x500)

// Hashing
struct RollingHash {
    uint64_t P;
    std::vector<uint64_t> p_pow, h;

    RollingHash(std::string_view s) {
        std::mt19937_64 rng(1337); // Fixed seed for reproducibility
        P = std::uniform_int_distribution<uint64_t>(37, 1000)(rng) * 2 + 1;

        int n = s.length();
        p_pow.resize(n + 1);
        h.resize(n + 1, 0);
        p_pow[0] = 1;

        for (int i = 0; i < n; ++i) {
            p_pow[i + 1] = (p_pow[i] * P);
            h[i + 1] = (h[i] * P + s[i]);
        }
    }

    uint64_t get(int i, int len) const {
        return h[i + len] - h[i] * p_pow[len];
    }
};

void hirschberg(std::string_view s1, std::string_view s2, std::string& transcript);

void banded_dp_pass(std::string_view s1, std::string_view s2, bool is_reversed, std::vector<int>& last_row) {
    int n = s1.length();
    int m = s2.length();
    
    last_row.assign(m + 1, 1e9);
    for (int j = 0; j <= std::min(m, BAND_WIDTH); ++j) last_row[j] = j;

    std::vector<int> prev_row = last_row;

    for (int i = 1; i <= n; ++i) {
        long long center_j_num = (long long)i * m;
        int center_j = center_j_num / n;
        int j_start = std::max(1, center_j - BAND_WIDTH);
        int j_end = std::min(m, center_j + BAND_WIDTH);
        
        last_row[0] = i;
        if(j_start > 1) last_row[j_start-1] = 1e9;


        for (int j = j_start; j <= j_end; ++j) {
            char c1 = is_reversed ? s1[n - i] : s1[i - 1];
            char c2 = is_reversed ? s2[m - j] : s2[j - 1];
            int cost = (c1 == c2) ? 0 : 1;
            
            int subst_val = prev_row[j - 1] + cost;
            int delete_val = prev_row[j] + 1;
            int insert_val = last_row[j - 1] + 1;
            last_row[j] = std::min({subst_val, delete_val, insert_val});
        }
        prev_row = last_row;
    }
}

void full_dp_traceback(std::string_view s1, std::string_view s2, std::string& transcript) {
    int n = s1.length();
    int m = s2.length();
    std::vector<std::vector<int>> dp(n + 1, std::vector<int>(m + 1));
    for (int i = 0; i <= n; ++i) dp[i][0] = i;
    for (int j = 0; j <= m; ++j) dp[0][j] = j;

    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= m; ++j) {
            int cost = (s1[i - 1] == s2[j - 1]) ? 0 : 1;
            dp[i][j] = std::min({dp[i - 1][j - 1] + cost, dp[i - 1][j] + 1, dp[i][j - 1] + 1});
        }
    }

    std::string T;
    T.reserve(n + m);
    int i = n, j = m;
    while (i > 0 || j > 0) {
        int cost = (i > 0 && j > 0 && s1[i - 1] == s2[j - 1]) ? 0 : 1;
        if (i > 0 && j > 0 && dp[i][j] == dp[i - 1][j - 1] + cost) {
            T += 'M';
            i--; j--;
        } else if (i > 0 && (j == 0 || dp[i][j] == dp[i - 1][j] + 1)) {
            T += 'D';
            i--;
        } else {
            T += 'I';
            j--;
        }
    }
    std::reverse(T.begin(), T.end());
    transcript += T;
}

void hirschberg(std::string_view s1, std::string_view s2, std::string& transcript) {
    int n = s1.length();
    int m = s2.length();

    if (n == 0) {
        transcript.append(m, 'I');
        return;
    }
    if (m == 0) {
        transcript.append(n, 'D');
        return;
    }
    if ((long long)n * m <= MAX_DP_SIZE) {
        full_dp_traceback(s1, s2, transcript);
        return;
    }

    if (n >= m) {
        int mid_n = n / 2;
        std::vector<int> fwd_costs, bwd_costs;
        banded_dp_pass(s1.substr(0, mid_n), s2, false, fwd_costs);
        
        std::string s1_rev_str(s1.substr(mid_n));
        std::string s2_rev_str(s2);
        std::reverse(s1_rev_str.begin(), s1_rev_str.end());
        std::reverse(s2_rev_str.begin(), s2_rev_str.end());

        banded_dp_pass(s1_rev_str, s2_rev_str, true, bwd_costs);
        std::reverse(bwd_costs.begin(), bwd_costs.end());

        int min_cost = 2e9;
        int mid_m = -1;
        for (int j = 0; j <= m; ++j) {
            if (fwd_costs[j] + bwd_costs[j] < min_cost) {
                min_cost = fwd_costs[j] + bwd_costs[j];
                mid_m = j;
            }
        }

        hirschberg(s1.substr(0, mid_n), s2.substr(0, mid_m), transcript);
        hirschberg(s1.substr(mid_n), s2.substr(mid_m), transcript);
    } else { // n < m, so we split s2
        int mid_m = m / 2;
        
        std::string s1_T(s1);
        std::vector<int> fwd_costs;
        banded_dp_pass(s2.substr(0, mid_m), s1_T, false, fwd_costs);

        std::string s2_T_bwd(s2.substr(mid_m));
        std::reverse(s1_T.begin(), s1_T.end());
        std::reverse(s2_T_bwd.begin(), s2_T_bwd.end());
        
        std::vector<int> bwd_costs;
        banded_dp_pass(s2_T_bwd, s1_T, true, bwd_costs);
        std::reverse(bwd_costs.begin(), bwd_costs.end());
        
        int min_cost = 2e9;
        int mid_n = -1;
        for (int i = 0; i <= n; ++i) {
            if (fwd_costs[i] + bwd_costs[i] < min_cost) {
                min_cost = fwd_costs[i] + bwd_costs[i];
                mid_n = i;
            }
        }
        
        hirschberg(s1.substr(0, mid_n), s2.substr(0, mid_m), transcript);
        hirschberg(s1.substr(mid_n), s2.substr(mid_m), transcript);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::string S1_str, S2_str;
    std::cin >> S1_str >> S2_str;
    std::string_view S1(S1_str);
    std::string_view S2(S2_str);

    int N = S1.length();
    int M = S2.length();

    RollingHash rh1(S1), rh2(S2);
    
    std::unordered_map<uint64_t, std::vector<int>> s2_hashes;
    if (M >= K_SEED) {
        for (int j = 0; j <= M - K_SEED; ++j) {
            s2_hashes[rh2.get(j, K_SEED)].push_back(j);
        }
    }
    
    std::vector<Match> mems;
    if (N >= K_SEED && M >= K_SEED) {
        for (int i = 0; i <= N - K_SEED; ++i) {
            uint64_t h = rh1.get(i, K_SEED);
            auto it = s2_hashes.find(h);
            if (it != s2_hashes.end()) {
                for (int j : it->second) {
                    int start_i = i, start_j = j;
                    while (start_i > 0 && start_j > 0 && S1[start_i - 1] == S2[start_j - 1]) {
                        start_i--; start_j--;
                    }
                    int end_i = i + K_SEED - 1, end_j = j + K_SEED - 1;
                    while (end_i + 1 < N && end_j + 1 < M && S1[end_i + 1] == S2[end_j + 1]) {
                        end_i++; end_j++;
                    }
                    int len = end_i - start_i + 1;
                    if (len >= MIN_MEM_LEN) {
                        mems.push_back({start_i, start_j, len});
                    }
                }
            }
        }
    }
    
    std::sort(mems.begin(), mems.end(), [](const Match& a, const Match& b) {
        return std::tie(a.i, a.j) < std::tie(b.i, b.j);
    });
    mems.erase(std::unique(mems.begin(), mems.end(), [](const Match& a, const Match& b) {
        return a.i == b.i && a.j == b.j;
    }), mems.end());
    
    std::sort(mems.begin(), mems.end(), [](const Match& a, const Match& b) {
        return a.len > b.len;
    });

    std::vector<Match> chain;
    std::set<std::pair<int, int>> covered_i, covered_j;
    for (const auto& m : mems) {
        auto it_i = covered_i.lower_bound({m.i, 0});
        bool overlap = false;
        if (it_i != covered_i.end() && it_i->first < m.i + m.len) overlap = true;
        if (it_i != covered_i.begin() && std::prev(it_i)->second > m.i) overlap = true;
        if (overlap) continue;
        
        auto it_j = covered_j.lower_bound({m.j, 0});
        if (it_j != covered_j.end() && it_j->first < m.j + m.len) overlap = true;
        if (it_j != covered_j.begin() && std::prev(it_j)->second > m.j) overlap = true;
        if (overlap) continue;

        chain.push_back(m);
        covered_i.insert({m.i, m.i + m.len});
        covered_j.insert({m.j, m.j + m.len});
    }

    std::sort(chain.begin(), chain.end(), [](const Match& a, const Match& b) {
        return a.i < b.i;
    });

    std::string transcript;
    transcript.reserve(N + M);

    int current_i = 0, current_j = 0;
    for (const auto& m : chain) {
        if (m.i > current_i || m.j > current_j) {
            hirschberg(S1.substr(current_i, m.i - current_i), S2.substr(current_j, m.j - current_j), transcript);
        }
        transcript.append(m.len, 'M');
        current_i = m.i + m.len;
        current_j = m.j + m.len;
    }

    if (current_i < N || current_j < M) {
        hirschberg(S1.substr(current_i), S2.substr(current_j), transcript);
    }

    std::cout << transcript << std::endl;

    return 0;
}