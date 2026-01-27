#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <tuple>

// Fast I/O to handle large inputs
namespace FastInput {
    constexpr int BUF_SIZE = 1 << 21; // 2MB buffer
    char in_buf[BUF_SIZE];
    char* in_ptr = in_buf + BUF_SIZE;

    char get_char() {
        if (in_ptr == in_buf + BUF_SIZE) {
            in_ptr = in_buf;
            int read_bytes = fread(in_buf, 1, BUF_SIZE, stdin);
            if (read_bytes < BUF_SIZE) {
                in_buf[read_bytes] = EOF;
            }
        }
        return *in_ptr++;
    }

    void read_string(std::string& s) {
        s.reserve(30000000);
        char c = get_char();
        while (c <= ' ') c = get_char();
        while (c > ' ') {
            s += c;
            c = get_char();
        }
    }
}

// Global variables to avoid passing large objects in recursion
std::string S1, S2;
std::vector<int> pos1[36], pos2[36];
std::vector<std::pair<int, int>> matches;
std::vector<std::pair<long long, int>> rarity;

// Heuristic parameters
const int RARE_LEVELS = 8;
const int MID_WINDOW = 5;
const int SMALL_PROBLEM_THRESHOLD = 50;


// Function to map characters 'A'-'Z', '0'-'9' to integers 0-35
int char_to_int(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return c - 'A' + 10;
}

// Forward declaration for mutual recursion
void solve_mid(int s1_l, int s1_r, int s2_l, int s2_r);

// Recursive solver using the "rarest character first" heuristic
void solve_rare(int s1_l, int s1_r, int s2_l, int s2_r, int level) {
    if (s1_l > s1_r || s2_l > s2_r) return;

    if (level >= RARE_LEVELS || (long long)(s1_r - s1_l) < SMALL_PROBLEM_THRESHOLD || (long long)(s2_r - s2_l) < SMALL_PROBLEM_THRESHOLD) {
        solve_mid(s1_l, s1_r, s2_l, s2_r);
        return;
    }

    int c_idx = rarity[level].second;

    auto it1_l = std::lower_bound(pos1[c_idx].begin(), pos1[c_idx].end(), s1_l);
    auto it1_r = std::upper_bound(pos1[c_idx].begin(), pos1[c_idx].end(), s1_r);

    auto it2_l = std::lower_bound(pos2[c_idx].begin(), pos2[c_idx].end(), s2_l);
    auto it2_r = std::upper_bound(pos2[c_idx].begin(), pos2[c_idx].end(), s2_r);

    if (it1_l == it1_r || it2_l == it2_r) {
        solve_rare(s1_l, s1_r, s2_l, s2_r, level + 1);
        return;
    }
    
    std::vector<std::pair<int, int>> current_matches;
    auto p2_it = it2_l;
    for (auto p1_it = it1_l; p1_it != it1_r; ++p1_it) {
        long long s1_pos = *p1_it;
        long long target_s2_pos = s2_l;
        if (s1_r > s1_l) {
             target_s2_pos += (s1_pos - s1_l) * (long long)(s2_r - s2_l) / (s1_r - s1_l);
        }
        
        p2_it = std::lower_bound(p2_it, it2_r, target_s2_pos);

        if (p2_it != it2_r) {
            current_matches.push_back({(int)s1_pos, *p2_it});
            p2_it++;
        } else {
            break;
        }
    }
    
    if (current_matches.empty()) {
        solve_rare(s1_l, s1_r, s2_l, s2_r, level + 1);
        return;
    }

    for (const auto& match : current_matches) {
        matches.push_back(match);
    }
    
    int last_s1 = s1_l - 1, last_s2 = s2_l - 1;
    for (const auto& match : current_matches) {
        solve_rare(last_s1 + 1, match.first - 1, last_s2 + 1, match.second - 1, level + 1);
        last_s1 = match.first;
        last_s2 = match.second;
    }
    solve_rare(last_s1 + 1, s1_r, last_s2 + 1, s2_r, level + 1);
}

// Recursive solver using "divide from middle" heuristic
void solve_mid(int s1_l, int s1_r, int s2_l, int s2_r) {
    if (s1_l > s1_r || s2_l > s2_r) return;
    
    if ((s1_r - s1_l < SMALL_PROBLEM_THRESHOLD) || (s2_r - s2_l < SMALL_PROBLEM_THRESHOLD)) {
        int cur_s2 = s2_l;
        for(int i = s1_l; i <= s1_r; ++i) {
            int c = char_to_int(S1[i]);
            auto it = std::lower_bound(pos2[c].begin(), pos2[c].end(), cur_s2);
            if(it != pos2[c].end() && *it <= s2_r) {
                matches.push_back({i, *it});
                cur_s2 = *it + 1;
            }
        }
        return;
    }

    bool s1_shorter = (s1_r - s1_l) <= (s2_r - s2_l);
    if (s1_shorter) {
        int s1_mid = s1_l + (s1_r - s1_l) / 2;
        int s1_pivot_idx = -1;
        int c_idx = -1;

        for (int d = 0; d <= MID_WINDOW; ++d) {
            if (s1_mid + d <= s1_r) {
                int cur_c_idx = char_to_int(S1[s1_mid + d]);
                auto it = std::lower_bound(pos2[cur_c_idx].begin(), pos2[cur_c_idx].end(), s2_l);
                if (it != pos2[cur_c_idx].end() && *it <= s2_r) {
                    s1_pivot_idx = s1_mid + d;
                    c_idx = cur_c_idx;
                    break;
                }
            }
            if (d > 0 && s1_mid - d >= s1_l) {
                int cur_c_idx = char_to_int(S1[s1_mid - d]);
                auto it = std::lower_bound(pos2[cur_c_idx].begin(), pos2[cur_c_idx].end(), s2_l);
                if (it != pos2[cur_c_idx].end() && *it <= s2_r) {
                    s1_pivot_idx = s1_mid - d;
                    c_idx = cur_c_idx;
                    break;
                }
            }
        }

        if (s1_pivot_idx != -1) {
            auto it_low = std::lower_bound(pos2[c_idx].begin(), pos2[c_idx].end(), s2_l);
            auto it_high = std::upper_bound(pos2[c_idx].begin(), pos2[c_idx].end(), s2_r);
            int count = std::distance(it_low, it_high);
            auto mid_it = it_low;
            std::advance(mid_it, count / 2);
            int s2_match_idx = *mid_it;
            
            matches.push_back({s1_pivot_idx, s2_match_idx});
            solve_mid(s1_l, s1_pivot_idx - 1, s2_l, s2_match_idx - 1);
            solve_mid(s1_pivot_idx + 1, s1_r, s2_match_idx + 1, s2_r);
        } else {
            solve_mid(s1_l, s1_mid - 1, s2_l, s2_r);
            solve_mid(s1_mid + 1, s1_r, s2_l, s2_r);
        }
    } else {
        int s2_mid = s2_l + (s2_r - s2_l) / 2;
        int s2_pivot_idx = -1;
        int c_idx = -1;

        for (int d = 0; d <= MID_WINDOW; ++d) {
            if (s2_mid + d <= s2_r) {
                int cur_c_idx = char_to_int(S2[s2_mid + d]);
                auto it = std::lower_bound(pos1[cur_c_idx].begin(), pos1[cur_c_idx].end(), s1_l);
                if (it != pos1[cur_c_idx].end() && *it <= s1_r) {
                    s2_pivot_idx = s2_mid + d;
                    c_idx = cur_c_idx;
                    break;
                }
            }
            if (d > 0 && s2_mid - d >= s2_l) {
                int cur_c_idx = char_to_int(S2[s2_mid - d]);
                auto it = std::lower_bound(pos1[cur_c_idx].begin(), pos1[cur_c_idx].end(), s1_l);
                if (it != pos1[cur_c_idx].end() && *it <= s1_r) {
                    s2_pivot_idx = s2_mid - d;
                    c_idx = cur_c_idx;
                    break;
                }
            }
        }
        
        if (s2_pivot_idx != -1) {
            auto it_low = std::lower_bound(pos1[c_idx].begin(), pos1[c_idx].end(), s1_l);
            auto it_high = std::upper_bound(pos1[c_idx].begin(), pos1[c_idx].end(), s1_r);
            int count = std::distance(it_low, it_high);
            auto mid_it = it_low;
            std::advance(mid_it, count / 2);
            int s1_match_idx = *mid_it;

            matches.push_back({s1_match_idx, s2_pivot_idx});
            solve_mid(s1_l, s1_match_idx - 1, s2_l, s2_pivot_idx - 1);
            solve_mid(s1_match_idx + 1, s1_r, s2_pivot_idx + 1, s2_r);
        } else {
            solve_mid(s1_l, s1_r, s2_l, s2_mid - 1);
            solve_mid(s1_l, s1_r, s2_mid + 1, s2_r);
        }
    }
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    FastInput::read_string(S1);
    FastInput::read_string(S2);

    for (int i = 0; i < S1.length(); ++i) {
        pos1[char_to_int(S1[i])].push_back(i);
    }
    for (int i = 0; i < S2.length(); ++i) {
        pos2[char_to_int(S2[i])].push_back(i);
    }

    for (int i = 0; i < 36; ++i) {
        if (!pos1[i].empty() && !pos2[i].empty()) {
            rarity.push_back({(long long)pos1[i].size() * pos2[i].size(), i});
        }
    }
    std::sort(rarity.begin(), rarity.end());

    solve_rare(0, S1.length() - 1, 0, S2.length() - 1, 0);

    std::sort(matches.begin(), matches.end());
    
    std::string res = "";
    if (!matches.empty()) {
        res.reserve(matches.size());
        for(const auto& p : matches) {
            res += S1[p.first];
        }
    }
    
    std::cout << res << "\n";

    return 0;
}