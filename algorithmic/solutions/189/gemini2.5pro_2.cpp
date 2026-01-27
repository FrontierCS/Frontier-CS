#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <string_view>
#include <unordered_map>
#include <tuple>

// A custom string view-like struct to handle reversed views efficiently,
// which is needed for Hirschberg's algorithm.
struct StrSlice {
    const std::string* str_ptr;
    int start;
    int len;
    bool reversed;

    StrSlice(const std::string& s) : str_ptr(&s), start(0), len(s.length()), reversed(false) {}
    StrSlice(const std::string* p, int s, int l, bool r = false) : str_ptr(p), start(s), len(l), reversed(r) {}

    char operator[](int i) const {
        return reversed ? (*str_ptr)[start + len - 1 - i] : (*str_ptr)[start + i];
    }

    int length() const {
        return len;
    }

    StrSlice substr(int pos, int count) const {
        if (reversed) {
            return StrSlice(str_ptr, start + len - (pos + count), count, true);
        }
        return StrSlice(str_ptr, start + pos, count, false);
    }

    StrSlice reverse() const {
        return StrSlice(str_ptr, start, len, !reversed);
    }
};

class EditDistanceApproximator {
private:
    const std::string& S1;
    const std::string& S2;
    const long long DP_THRESHOLD = 2500000;

    // Hirschberg's algorithm for optimal alignment on small subproblems
    std::string hirschberg(StrSlice s1v, StrSlice s2v) {
        int n = s1v.length();
        int m = s2v.length();

        if (n == 0) return std::string(m, 'I');
        if (m == 0) return std::string(n, 'D');

        if (n == 1) {
            int min_cost = m;
            int best_j = -1; // -1 indicates deleting s1v[0] is best
            for (int j = 0; j < m; ++j) {
                int cost = j + (m - 1 - j) + (s1v[0] != s2v[j]);
                if (cost < min_cost) {
                    min_cost = cost;
                    best_j = j;
                }
            }
            if (1 + m <= min_cost) {
                return 'D' + std::string(m, 'I');
            }
            
            std::string res = "";
            if (best_j > 0) res += std::string(best_j, 'I');
            res += 'M';
            if (m - 1 - best_j > 0) res += std::string(m - 1 - best_j, 'I');
            return res;
        }

        int mid = n / 2;
        StrSlice s1_left = s1v.substr(0, mid);
        StrSlice s1_right = s1v.substr(mid, n - mid);

        std::vector<int> left_costs = calculate_dp_row(s1_left, s2v);
        std::vector<int> right_costs = calculate_dp_row(s1_right.reverse(), s2v.reverse());
        std::reverse(right_costs.begin(), right_costs.end());

        int mid_j = 0;
        int min_total_cost = -1;

        for (int j = 0; j <= m; ++j) {
            if (min_total_cost == -1 || left_costs[j] + right_costs[j] < min_total_cost) {
                min_total_cost = left_costs[j] + right_costs[j];
                mid_j = j;
            }
        }

        StrSlice s2_left = s2v.substr(0, mid_j);
        StrSlice s2_right = s2v.substr(mid_j, m - mid_j);

        return hirschberg(s1_left, s2_left) + hirschberg(s1_right, s2_right);
    }

    // Standard space-optimized DP row calculation for Levenshtein distance
    std::vector<int> calculate_dp_row(StrSlice s1v, StrSlice s2v) {
        int n = s1v.length();
        int m = s2v.length();
        std::vector<int> prev_row(m + 1);
        std::vector<int> curr_row(m + 1);

        for (int j = 0; j <= m; ++j) prev_row[j] = j;

        for (int i = 1; i <= n; ++i) {
            curr_row[0] = i;
            for (int j = 1; j <= m; ++j) {
                int cost = (s1v[i - 1] == s2v[j - 1]) ? 0 : 1;
                curr_row[j] = std::min({ prev_row[j] + 1, curr_row[j - 1] + 1, prev_row[j - 1] + cost });
            }
            prev_row = curr_row;
        }
        return prev_row;
    }

    // Fallback alignment for dissimilar regions
    std::string greedy_align(int n, int m) {
        std::string res = "";
        int common_len = std::min(n, m);
        if (common_len > 0) res.append(common_len, 'M');
        if (n > m) res.append(n - m, 'D');
        else if (m > n) res.append(m - n, 'I');
        return res;
    }

    struct Anchor { int s1_pos, s2_pos, len; };

    // Find and chain anchors greedily
    std::vector<Anchor> find_anchors(int s1_b, int s1_e, int s2_b, int s2_e, int B) {
        int n = s1_e - s1_b;
        int m = s2_e - s2_b;
        if (n < B || m < B) return {};

        const uint64_t P = 37;
        uint64_t P_B = 1;
        for (int i = 0; i < B; ++i) P_B *= P;

        std::unordered_map<uint64_t, std::vector<int>> s2_kmers;
        if (m > B) s2_kmers.reserve(m - B + 1);
        
        uint64_t h = 0;
        for (int j = 0; j < B; ++j) h = h * P + S2[s2_b + j];
        s2_kmers[h].push_back(s2_b);
        for (int j = B; j < m; ++j) {
            h = h * P + S2[s2_b + j] - P_B * S2[s2_b + j - B];
            s2_kmers[h].push_back(s2_b + j - B + 1);
        }
        
        std::vector<std::pair<int, int>> matches;
        h = 0;
        for (int i = 0; i < B; ++i) h = h * P + S1[s1_b + i];
        if (s2_kmers.count(h)) {
            for (int s2_pos : s2_kmers.at(h)) {
                matches.push_back({s1_b, s2_pos});
            }
        }
        for (int i = B; i < n; ++i) {
            h = h * P + S1[s1_b + i] - P_B * S1[s1_b + i - B];
            if (s2_kmers.count(h)) {
                for (int s2_pos : s2_kmers.at(h)) {
                    matches.push_back({s1_b + i - B + 1, s2_pos});
                }
            }
        }

        if (matches.empty()) return {};
        
        std::sort(matches.begin(), matches.end(), [](const auto& a, const auto& b){
            return (a.first + a.second) < (b.first + b.second);
        });

        std::vector<Anchor> chain;
        int current_s1 = s1_b;
        int current_s2 = s2_b;
        for (const auto& match : matches) {
            if (match.first >= current_s1 && match.second >= current_s2) {
                chain.push_back({match.first, match.second, B});
                current_s1 = match.first + B;
                current_s2 = match.second + B;
            }
        }
        return chain;
    }

    // Main recursive solver
    std::string solve_recursive(int s1_b, int s1_e, int s2_b, int s2_e) {
        int n = s1_e - s1_b;
        int m = s2_e - s2_b;

        if (n == 0) return std::string(m, 'I');
        if (m == 0) return std::string(n, 'D');

        if ((long long)n * m <= DP_THRESHOLD) {
            return hirschberg(StrSlice(&S1, s1_b, n), StrSlice(&S2, s2_b, m));
        }

        int B = 12;
        if ((long long)n * m > 100000000LL) B = 16;
        
        std::vector<Anchor> anchors = find_anchors(s1_b, s1_e, s2_b, s2_e, B);
        if (anchors.empty() && B > 8) {
            anchors = find_anchors(s1_b, s1_e, s2_b, s2_e, 8);
        }

        if (anchors.empty()) {
            return greedy_align(n, m);
        }

        std::string res = "";
        int current_s1 = s1_b;
        int current_s2 = s2_b;
        for (const auto& anchor : anchors) {
            if (anchor.s1_pos > current_s1 || anchor.s2_pos > current_s2) {
                res += solve_recursive(current_s1, anchor.s1_pos, current_s2, anchor.s2_pos);
            }
            res += std::string(anchor.len, 'M');
            current_s1 = anchor.s1_pos + anchor.len;
            current_s2 = anchor.s2_pos + anchor.len;
        }
        if (s1_e > current_s1 || s2_e > current_s2) {
            res += solve_recursive(current_s1, s1_e, current_s2, s2_e);
        }
        
        return res;
    }

public:
    EditDistanceApproximator(const std::string& s1, const std::string& s2) : S1(s1), S2(s2) {}

    std::string calculate_transcript() {
        return solve_recursive(0, S1.length(), 0, S2.length());
    }
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::string s1, s2;
    std::cin >> s1 >> s2;
    
    EditDistanceApproximator solver(s1, s2);
    std::cout << solver.calculate_transcript() << std::endl;

    return 0;
}