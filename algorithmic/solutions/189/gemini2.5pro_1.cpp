#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <unordered_map>
#include <string_view>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

string s1_global, s2_global;

// Forward declaration
string solve(string_view s1, string_view s2);

// Standard DP with path reconstruction for small cases
string dp_solve(string_view s1, string_view s2) {
    int n = s1.length();
    int m = s2.length();
    if (n == 0) return string(m, 'I');
    if (m == 0) return string(n, 'D');

    vector<vector<uint16_t>> dp(n + 1, vector<uint16_t>(m + 1));
    vector<vector<char>> path(n + 1, vector<char>(m + 1));

    for (int i = 0; i <= n; ++i) {
        dp[i][0] = i;
        path[i][0] = 'D';
    }
    for (int j = 0; j <= m; ++j) {
        dp[0][j] = j;
        path[0][j] = 'I';
    }
    path[0][0] = 0;

    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= m; ++j) {
            uint16_t cost = (s1[i - 1] == s2[j - 1]) ? 0 : 1;
            uint16_t match_cost = dp[i - 1][j - 1] + cost;
            uint16_t delete_cost = dp[i - 1][j] + 1;
            uint16_t insert_cost = dp[i][j - 1] + 1;
            
            if (match_cost <= delete_cost && match_cost <= insert_cost) {
                dp[i][j] = match_cost;
                path[i][j] = 'M';
            } else if (delete_cost <= insert_cost) {
                dp[i][j] = delete_cost;
                path[i][j] = 'D';
            } else {
                dp[i][j] = insert_cost;
                path[i][j] = 'I';
            }
        }
    }

    string transcript = "";
    int i = n, j = m;
    while (i > 0 || j > 0) {
        char move = path[i][j];
        transcript += move;
        if (move == 'M') { i--; j--; } 
        else if (move == 'D') { i--; } 
        else { j--; }
    }
    reverse(transcript.begin(), transcript.end());
    return transcript;
}

// Hirschberg's algorithm for optimal alignment in O(N*M) time and O(min(N,M)) space
string hirschberg(string_view s1, string_view s2) {
    int n = s1.length();
    int m = s2.length();

    if (n == 0) return string(m, 'I');
    if (m == 0) return string(n, 'D');
    
    if ((long long)n * m <= 2500 || min(n, m) <= 5) {
        return dp_solve(s1, s2);
    }
    
    if (n > m) {
        int mid = n / 2;
        vector<int> score_l(m + 1), score_r(m + 1);

        for (int j = 0; j <= m; j++) score_l[j] = j;
        for (int i = 1; i <= mid; i++) {
            int prev = score_l[0];
            score_l[0]++;
            for (int j = 1; j <= m; j++) {
                int cost = (s1[i - 1] == s2[j - 1]) ? 0 : 1;
                int temp = score_l[j];
                score_l[j] = min({score_l[j] + 1, score_l[j-1] + 1, prev + cost});
                prev = temp;
            }
        }
        
        for (int j = 0; j <= m; j++) score_r[j] = j;
        for (int i = 1; i <= n - mid; i++) {
            int prev = score_r[0];
            score_r[0]++;
            for (int j = 1; j <= m; j++) {
                int cost = (s1[n - i] == s2[m - j]) ? 0 : 1;
                int temp = score_r[j];
                score_r[j] = min({score_r[j] + 1, score_r[j-1] + 1, prev + cost});
                prev = temp;
            }
        }

        int split_j = -1, min_score = -1;
        for (int j = 0; j <= m; j++) {
            if (split_j == -1 || score_l[j] + score_r[m - j] < min_score) {
                min_score = score_l[j] + score_r[m - j];
                split_j = j;
            }
        }
        return hirschberg(s1.substr(0, mid), s2.substr(0, split_j)) + hirschberg(s1.substr(mid), s2.substr(split_j));

    } else { // n <= m
        int mid = n / 2;
        vector<int> score_l(m + 1), score_r(m + 1);

        for (int j = 0; j <= m; j++) score_l[j] = j;
        for (int i = 1; i <= mid; i++) {
            int prev = score_l[0];
            score_l[0]++;
            for (int j = 1; j <= m; j++) {
                int cost = (s1[i - 1] == s2[j - 1]) ? 0 : 1;
                int temp = score_l[j];
                score_l[j] = min({score_l[j] + 1, score_l[j-1] + 1, prev + cost});
                prev = temp;
            }
        }
        
        for (int j = 0; j <= m; j++) score_r[j] = j;
        for (int i = 1; i <= n - mid; i++) {
            int prev = score_r[0];
            score_r[0]++;
            for (int j = 1; j <= m; j++) {
                int cost = (s1[n - i] == s2[m - j]) ? 0 : 1;
                int temp = score_r[j];
                score_r[j] = min({score_r[j] + 1, score_r[j-1] + 1, prev + cost});
                prev = temp;
            }
        }
        
        int split_j = -1, min_score = -1;
        for (int j = 0; j <= m; j++) {
            if (split_j == -1 || score_l[j] + score_r[m - j] < min_score) {
                min_score = score_l[j] + score_r[m - j];
                split_j = j;
            }
        }
        return hirschberg(s1.substr(0, mid), s2.substr(0, split_j)) + hirschberg(s1.substr(mid), s2.substr(split_j));
    }
}

const int K_MER_SIZE = 12;
const long long HIRSCHBERG_THRESHOLD = 4000000;
unordered_map<uint64_t, vector<int>> s2_kmer_index;
const uint64_t B = 37;
uint64_t B_power_K;

void build_kmer_index(string_view s) {
    if (s.length() < K_MER_SIZE) return;
    
    uint64_t current_hash = 0;
    for (int i = 0; i < K_MER_SIZE; ++i) {
        current_hash = current_hash * B + s[i];
    }
    s2_kmer_index[current_hash].push_back(0);
    
    B_power_K = 1;
    for (int i = 0; i < K_MER_SIZE; ++i) B_power_K *= B;

    for (size_t i = 1; i <= s.length() - K_MER_SIZE; ++i) {
        current_hash = current_hash * B - s[i - 1] * B_power_K + s[i + K_MER_SIZE - 1];
        s2_kmer_index[current_hash].push_back(i);
    }
}

string solve(string_view s1, string_view s2) {
    int n = s1.length();
    int m = s2.length();

    if (n == 0) return string(m, 'I');
    if (m == 0) return string(n, 'D');

    if ((long long)n * m < HIRSCHBERG_THRESHOLD || min(n, m) < K_MER_SIZE * 2) {
        return hirschberg(s1, s2);
    }
    
    int s1_mid = n / 2;
    string_view mid_kmer_sv = s1.substr(s1_mid, K_MER_SIZE);

    uint64_t mid_kmer_hash = 0;
    for (char c : mid_kmer_sv) {
        mid_kmer_hash = mid_kmer_hash * B + c;
    }
    
    int best_s2_pos = -1;
    if (s2_kmer_index.count(mid_kmer_hash)) {
        const auto& positions = s2_kmer_index.at(mid_kmer_hash);
        size_t s2_offset = s2.data() - s2_global.data();
        int s2_target_pos = (double)m / n * s1_mid;
        
        int min_dist = -1;
        
        auto it = lower_bound(positions.begin(), positions.end(), s2_offset + s2_target_pos);
        
        for (int k = 0; k < 10 && it != positions.end(); ++k, ++it) {
            int pos = *it;
            if (pos >= (int)s2_offset && pos <= (int)s2_offset + m - K_MER_SIZE) {
                if (string_view(s2_global.data() + pos, K_MER_SIZE) == mid_kmer_sv) {
                    int dist = abs((pos - (int)s2_offset) - s2_target_pos);
                    if (min_dist == -1 || dist < min_dist) {
                        min_dist = dist;
                        best_s2_pos = pos - s2_offset;
                    }
                }
            }
        }

        it = lower_bound(positions.begin(), positions.end(), s2_offset + s2_target_pos);
        if (it != positions.begin()) {
            it--;
            for (int k = 0; k < 10; ++k) {
                int pos = *it;
                if (pos >= (int)s2_offset && pos <= (int)s2_offset + m - K_MER_SIZE) {
                    if (string_view(s2_global.data() + pos, K_MER_SIZE) == mid_kmer_sv) {
                        int dist = abs((pos - (int)s2_offset) - s2_target_pos);
                        if (min_dist == -1 || dist < min_dist) {
                            min_dist = dist;
                            best_s2_pos = pos - s2_offset;
                        }
                    }
                }
                if (it == positions.begin()) break;
                it--;
            }
        }
    }

    if (best_s2_pos != -1) {
        int s1_anchor_start = s1_mid;
        int s2_anchor_start = best_s2_pos;

        while (s1_anchor_start > 0 && s2_anchor_start > 0 && s1[s1_anchor_start - 1] == s2[s2_anchor_start - 1]) {
            s1_anchor_start--;
            s2_anchor_start--;
        }

        int s1_anchor_end = s1_mid + K_MER_SIZE;
        int s2_anchor_end = best_s2_pos + K_MER_SIZE;
        while (s1_anchor_end < n && s2_anchor_end < m && s1[s1_anchor_end] == s2[s2_anchor_end]) {
            s1_anchor_end++;
            s2_anchor_end++;
        }

        string res1 = solve(s1.substr(0, s1_anchor_start), s2.substr(0, s2_anchor_start));
        string res_match = string(s1_anchor_end - s1_anchor_start, 'M');
        string res2 = solve(s1.substr(s1_anchor_end), s2.substr(s2_anchor_end));
        return res1 + res_match + res2;
    } else {
        int s2_mid = (long long)m * s1_mid / n;
        string res1 = solve(s1.substr(0, s1_mid), s2.substr(0, s2_mid));
        string res2 = solve(s1.substr(s1_mid), s2.substr(s2_mid));
        return res1 + res2;
    }
}

int main() {
    fast_io();
    cin >> s1_global >> s2_global;

    bool swapped = false;
    if (s1_global.length() > s2_global.length()) {
        swap(s1_global, s2_global);
        swapped = true;
    }
    
    build_kmer_index(s2_global);
    string result = solve(s1_global, s2_global);

    if (swapped) {
        for (char& c : result) {
            if (c == 'I') c = 'D';
            else if (c == 'D') c = 'I';
        }
    }

    cout << result << "\n";

    return 0;
}