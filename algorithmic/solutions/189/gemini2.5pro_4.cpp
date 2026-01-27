#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <string_view>
#include <chrono>
#include <random>

// Global strings and transcript buffer
std::string S1, S2;
std::vector<char> T_buffer;

// Constants for the algorithm
const long long HIRSCHBERG_THRESHOLD_NM = 20000000LL;
const int MIN_LCS_LEN = 12;

// --- Rolling Hash Implementation ---
struct Hasher {
    long long P1, M1 = 1e9 + 7;
    long long P2, M2 = 1e9 + 9;
    std::vector<long long> p1_pows, p2_pows;
    std::vector<long long> h1, h2;

    Hasher(std::string_view s, long long p1, long long p2) : P1(p1), P2(p2) {
        int n = s.length();
        p1_pows.resize(n + 1);
        p2_pows.resize(n + 1);
        h1.resize(n + 1, 0);
        h2.resize(n + 1, 0);

        p1_pows[0] = 1;
        p2_pows[0] = 1;
        for (int i = 1; i <= n; ++i) {
            p1_pows[i] = (p1_pows[i - 1] * P1) % M1;
            p2_pows[i] = (p2_pows[i - 1] * P2) % M2;
        }

        for (int i = 0; i < n; ++i) {
            int char_val = (s[i] >= 'A' && s[i] <= 'Z') ? (s[i] - 'A') : (s[i] - '0' + 26);
            h1[i + 1] = (h1[i] * P1 + char_val + 1) % M1;
            h2[i + 1] = (h2[i] * P2 + char_val + 1) % M2;
        }
    }

    std::pair<long long, long long> get_hash(int i, int len) {
        long long res1 = (h1[i + len] - (h1[i] * p1_pows[len]) % M1 + M1) % M1;
        long long res2 = (h2[i + len] - (h2[i] * p2_pows[len]) % M2 + M2) % M2;
        return {res1, res2};
    }
};

// --- Hirschberg's Algorithm ---
void hirschberg_dp_row(std::string_view s1, std::string_view s2, std::vector<int>& last_row) {
    int n = s1.length();
    int m = s2.length();
    last_row.assign(m + 1, 0);
    std::vector<int> curr_row(m + 1, 0);

    for (int j = 0; j <= m; ++j) {
        last_row[j] = j;
    }

    for (int i = 1; i <= n; ++i) {
        curr_row[0] = i;
        for (int j = 1; j <= m; ++j) {
            if (s1[i - 1] == s2[j - 1]) {
                curr_row[j] = last_row[j - 1];
            } else {
                curr_row[j] = 1 + std::min({last_row[j], curr_row[j-1], last_row[j-1]});
            }
        }
        last_row = curr_row;
    }
}

void hirschberg(std::string_view s1, std::string_view s2) {
    int n = s1.length();
    int m = s2.length();

    if (n == 0) {
        for (int i = 0; i < m; ++i) T_buffer.push_back('I');
        return;
    }
    if (m == 0) {
        for (int i = 0; i < n; ++i) T_buffer.push_back('D');
        return;
    }
    if (n == 1) {
        size_t pos = s2.find(s1[0]);
        if (pos == std::string_view::npos) {
            pos = 0;
        }
        for (size_t i = 0; i < pos; ++i) T_buffer.push_back('I');
        T_buffer.push_back('M');
        for (size_t i = pos + 1; i < m; ++i) T_buffer.push_back('I');
        return;
    }
    
    int mid = n / 2;
    std::vector<int> fwd_costs, bwd_costs;
    hirschberg_dp_row(s1.substr(0, mid), s2, fwd_costs);

    std::string s1_rev_str(s1.substr(mid));
    std::reverse(s1_rev_str.begin(), s1_rev_str.end());
    std::string s2_rev_str(s2);
    std::reverse(s2_rev_str.begin(), s2_rev_str.end());
    hirschberg_dp_row(s1_rev_str, s2_rev_str, bwd_costs);

    int split_j = -1;
    int min_total_cost = 1e9 + 7;
    for (int j = 0; j <= m; ++j) {
        int total_cost = fwd_costs[j] + bwd_costs[m - j];
        if (total_cost < min_total_cost) {
            min_total_cost = total_cost;
            split_j = j;
        }
    }
    
    hirschberg(s1.substr(0, mid), s2.substr(0, split_j));
    hirschberg(s1.substr(mid), s2.substr(split_j));
}

// --- LCSk Finder ---
struct LCSkResult {
    int len = 0, pos1 = -1, pos2 = -1;
};

LCSkResult find_lcs(int i1, int i2, int j1, int j2, long long p1, long long p2) {
    int n = i2 - i1 + 1;
    int m = j2 - j1 + 1;
    if (n < MIN_LCS_LEN || m < MIN_LCS_LEN) return {};
    
    Hasher hasher1(std::string_view(&S1[i1], n), p1, p2);
    Hasher hasher2(std::string_view(&S2[j1], m), p1, p2);
    
    int low = MIN_LCS_LEN, high = std::min(n, m);
    LCSkResult result;

    while (low <= high) {
        int L = low + (high - low) / 2;
        if (L == 0) break;
        std::vector<std::pair<std::pair<long long, long long>, int>> s1_hashes;
        s1_hashes.reserve(n-L+1);
        for (int i = 0; i <= n - L; ++i) {
            s1_hashes.push_back({hasher1.get_hash(i, L), i});
        }
        std::sort(s1_hashes.begin(), s1_hashes.end());
        
        bool found = false;
        
        int center_m = (m - L) / 2;
        for (int k = 0; k <= center_m; ++k) {
            int fwd_idx = center_m + k;
            if (fwd_idx <= m - L) {
                auto h = hasher2.get_hash(fwd_idx, L);
                auto it = std::lower_bound(s1_hashes.begin(), s1_hashes.end(), std::make_pair(h, 0));
                if (it != s1_hashes.end() && it->first == h) {
                    found = true;
                    result = {L, i1 + it->second, j1 + fwd_idx};
                    break;
                }
            }
            if (k > 0) {
                int bwd_idx = center_m - k;
                if (bwd_idx >= 0) {
                    auto h = hasher2.get_hash(bwd_idx, L);
                    auto it = std::lower_bound(s1_hashes.begin(), s1_hashes.end(), std::make_pair(h, 0));
                    if (it != s1_hashes.end() && it->first == h) {
                        found = true;
                        result = {L, i1 + it->second, j1 + bwd_idx};
                        break;
                    }
                }
            }
        }
        
        if (found) {
            low = L + 1;
        } else {
            high = L - 1;
        }
    }

    return result;
}

// --- Main Recursive Solver ---
void solve(int i1, int i2, int j1, int j2, long long p1, long long p2) {
    int n = i2 - i1 + 1;
    int m = j2 - j1 + 1;

    if (n <= 0) {
        for (int i = 0; i < m; ++i) T_buffer.push_back('I');
        return;
    }
    if (m <= 0) {
        for (int i = 0; i < n; ++i) T_buffer.push_back('D');
        return;
    }

    if ((long long)n * m < HIRSCHBERG_THRESHOLD_NM) {
        hirschberg(std::string_view(&S1[i1], n), std::string_view(&S2[j1], m));
        return;
    }

    LCSkResult lcs = find_lcs(i1, i2, j1, j2, p1, p2);

    if (lcs.len < MIN_LCS_LEN) {
        hirschberg(std::string_view(&S1[i1], n), std::string_view(&S2[j1], m));
        return;
    }

    solve(i1, lcs.pos1 - 1, j1, lcs.pos2 - 1, p1, p2);
    for (int i = 0; i < lcs.len; ++i) {
        T_buffer.push_back('M');
    }
    solve(lcs.pos1 + lcs.len, i2, lcs.pos2 + lcs.len, j2, p1, p2);
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> S1 >> S2;
    T_buffer.reserve(S1.length() + S2.length());

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    long long p1 = std::uniform_int_distribution<long long>(37, 1000)(rng);
    long long p2 = std::uniform_int_distribution<long long>(37, 1000)(rng);
    if (p1 == p2) p2++;

    solve(0, S1.length() - 1, 0, S2.length() - 1, p1, p2);

    for (char c : T_buffer) {
        std::cout << c;
    }
    std::cout << '\n';

    return 0;
}