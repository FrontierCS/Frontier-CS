#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <cmath>

// Fast I/O
void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

// Global strings and their integer representations for hashing
std::string S1, S2;
std::vector<int> S1_int, S2_int;

// Convert characters 'A'-'Z', '0'-'9' to integers 1-36
void convert_strings_to_ints() {
    S1_int.reserve(S1.length());
    for (char c : S1) {
        if (c >= 'A' && c <= 'Z') S1_int.push_back(c - 'A' + 1);
        else S1_int.push_back(c - '0' + 27);
    }
    S2_int.reserve(S2.length());
    for (char c : S2) {
        if (c >= 'A' && c <= 'Z') S2_int.push_back(c - 'A' + 1);
        else S2_int.push_back(c - '0' + 27);
    }
}

// Hashing parameters and precomputed powers for rolling hash
const long long P1 = 37, M1 = 1e9 + 7;
const long long P2 = 43, M2 = 1e9 + 9;
std::vector<long long> p1_pows, p2_pows;

void precompute_powers(int max_len) {
    p1_pows.resize(max_len + 1);
    p2_pows.resize(max_len + 1);
    p1_pows[0] = 1;
    p2_pows[0] = 1;
    for (int i = 1; i <= max_len; ++i) {
        p1_pows[i] = (p1_pows[i-1] * P1) % M1;
        p2_pows[i] = (p2_pows[i-1] * P2) % M2;
    }
}

// Dual-hash structure for collision reduction
struct Hash {
    long long h1, h2;
    bool operator==(const Hash& other) const { return h1 == other.h1 && h2 == other.h2; }
};

// Calculates hash of a substring
Hash get_hash(const std::vector<int>& s, int start, int len) {
    long long h1 = 0, h2 = 0;
    for (int i = 0; i < len; ++i) {
        h1 = (h1 * P1 + s[start + i]) % M1;
        h2 = (h2 * P2 + s[start + i]) % M2;
    }
    return {h1, h2};
}

// Defines a subproblem to be solved
struct Job {
    int s1_start, s1_end, s2_start, s2_end;
};

// Represents a solved segment (either a match or an unmatchable region)
struct Segment {
    int s1_start, s1_end, s2_start, s2_end;
    bool is_match;
    bool operator<(const Segment& other) const {
        if (s1_start != other.s1_start) {
            return s1_start < other.s1_start;
        }
        return s2_start < other.s2_start;
    }
};

// Finds one good common substring to use as an anchor
std::pair<std::pair<int, int>, int> find_match(int s1_start, int s1_end, int s2_start, int s2_end) {
    int n = s1_end - s1_start + 1;
    int m = s2_end - s2_start + 1;
    const int B = 16;
    if (n < B || m < B) return {{-1, -1}, 0};

    std::pair<std::pair<int, int>, int> best_match = {{-1, -1}, 0};

    // Probe S1 at different locations to find a potential match
    int probes[] = {n / 2, n / 4, 3 * n / 4};
    for (int p : probes) {
        int s1_probe_start = s1_start + p;
        if (s1_probe_start < s1_start || s1_probe_start + B > s1_end + 1) continue;

        Hash s1_probe_hash = get_hash(S1_int, s1_probe_start, B);

        // Find occurrences in S2 using rolling hash
        std::vector<int> s2_match_indices;
        if (m >= B) {
            Hash s2_rolling_hash = get_hash(S2_int, s2_start, B);
            if (s2_rolling_hash == s1_probe_hash) {
                s2_match_indices.push_back(s2_start);
            }
            for (int i = s2_start + 1; i <= s2_end - B + 1; ++i) {
                long long h1 = s2_rolling_hash.h1;
                h1 = (h1 - (1LL * S2_int[i - 1] * p1_pows[B - 1]) % M1 + M1) % M1;
                h1 = (h1 * P1 + S2_int[i + B - 1]) % M1;
                long long h2 = s2_rolling_hash.h2;
                h2 = (h2 - (1LL * S2_int[i - 1] * p2_pows[B - 1]) % M2 + M2) % M2;
                h2 = (h2 * P2 + S2_int[i + B - 1]) % M2;
                s2_rolling_hash = {h1, h2};
                if (s2_rolling_hash == s1_probe_hash) {
                    s2_match_indices.push_back(i);
                }
                if (s2_match_indices.size() > 500) break; // Optimization for very common substrings
            }
        }
        
        if (s2_match_indices.empty()) continue;

        // Heuristic: pick the S2 match closest to the "diagonal"
        double expected_s2_relative = (double)(s1_probe_start - s1_start) / n * m;
        int best_s2_pos = -1;
        double min_dist = 1e18;

        for (int s2_pos : s2_match_indices) {
            double dist = std::abs((s2_pos - s2_start) - expected_s2_relative);
            if (dist < min_dist) {
                min_dist = dist;
                best_s2_pos = s2_pos;
            }
        }

        // Extend the B-length match in both directions
        int s1_match_start = s1_probe_start, s2_match_start = best_s2_pos;
        int len = B;
        
        while (s1_match_start > s1_start && s2_match_start > s2_start && S1[s1_match_start - 1] == S2[s2_match_start - 1]) {
            s1_match_start--; s2_match_start--; len++;
        }
        
        int s1_match_end = s1_probe_start + B - 1, s2_match_end = best_s2_pos + B - 1;
        while (s1_match_end < s1_end && s2_match_end < s2_end && S1[s1_match_end + 1] == S2[s2_match_end + 1]) {
            s1_match_end++; s2_match_end++; len++;
        }

        if (len > best_match.second) {
            best_match = {{s1_match_start, s2_match_start}, len};
        }
    }
    return best_match;
}

// Fast, greedy alignment for unmatchable regions
void greedy_append(std::string& T, int s1_start, int s1_end, int s2_start, int s2_end) {
    int n = s1_end - s1_start + 1;
    int m = s2_end - s2_start + 1;

    if (n <= 0 && m <= 0) return;
    if (n <= 0) { T.append(m, 'I'); return; }
    if (m <= 0) { T.append(n, 'D'); return; }
    
    int i = s1_start, j = s2_start;
    while (i <= s1_end && j <= s2_end) {
        int rem_n = s1_end - i + 1;
        int rem_m = s2_end - j + 1;
        if (rem_n > rem_m) {
            T += 'D'; i++;
        } else if (rem_m > rem_n) {
            T += 'I'; j++;
        } else {
            T += 'M'; i++; j++;
        }
    }
    while (i <= s1_end) { T += 'D'; i++; }
    while (j <= s2_end) { T += 'I'; j++; }
}


int main() {
    fast_io();
    std::cin >> S1 >> S2;
    int N = S1.length();
    int M = S2.length();
    
    convert_strings_to_ints();
    precompute_powers(std::max(N, M));
    
    std::vector<Job> jobs;
    if (N > 0 || M > 0) {
        jobs.push_back({0, N - 1, 0, M - 1});
    }
    
    std::vector<Segment> segments;
    
    const int MIN_MATCH_LEN = 24;

    while (!jobs.empty()) {
        Job job = jobs.back();
        jobs.pop_back();

        if (job.s1_start > job.s1_end && job.s2_start > job.s2_end) continue;
        
        auto [pos, len] = find_match(job.s1_start, job.s1_end, job.s2_start, job.s2_end);

        if (len < MIN_MATCH_LEN) {
            segments.push_back({job.s1_start, job.s1_end, job.s2_start, job.s2_end, false});
            continue;
        }

        int s1_match_start = pos.first;
        int s2_match_start = pos.second;
        
        segments.push_back({s1_match_start, s1_match_start + len - 1, s2_match_start, s2_match_start + len - 1, true});

        // Add subproblems for regions before and after the match
        if (s1_match_start > job.s1_start || s2_match_start > job.s2_start) {
            jobs.push_back({job.s1_start, s1_match_start - 1, job.s2_start, s2_match_start - 1});
        }
        if (s1_match_start + len <= job.s1_end || s2_match_start + len <= job.s2_end) {
            jobs.push_back({s1_match_start + len, job.s1_end, s2_match_start + len, job.s2_end});
        }
    }
    
    std::sort(segments.begin(), segments.end());
    
    std::string T;
    T.reserve(N + M);
    
    int current_i = 0, current_j = 0;
    for (const auto& seg : segments) {
        if (seg.s1_start < current_i || seg.s2_start < current_j) continue;
        
        // Greedily align the gap before the current segment
        greedy_append(T, current_i, seg.s1_start - 1, current_j, seg.s2_start - 1);
        
        if (seg.is_match) {
            T.append(seg.s1_end - seg.s1_start + 1, 'M');
        } else {
            greedy_append(T, seg.s1_start, seg.s1_end, seg.s2_start, seg.s2_end);
        }
        
        current_i = seg.s1_end + 1;
        current_j = seg.s2_end + 1;
    }
    
    // Greedily align the final remaining gap
    greedy_append(T, current_i, N - 1, current_j, M - 1);
    
    std::cout << T << '\n';

    return 0;
}