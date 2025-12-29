#include <bits/stdc++.h>
using namespace std;

static inline bool is_space(char c) {
    return c==' ' || c=='\t' || c=='\n' || c=='\r' || c=='\v' || c=='\f';
}

static vector<string> split_lines(const string &s) {
    vector<string> lines;
    string line;
    for (size_t i = 0; i < s.size(); ++i) {
        if (s[i] == '\n') {
            lines.push_back(line);
            line.clear();
        } else if (s[i] != '\r') {
            line.push_back(s[i]);
        }
    }
    if (!line.empty() || (!s.empty() && s.back()=='\n')) lines.push_back(line);
    return lines;
}

static vector<long long> parse_ints_from_line(const string &line) {
    vector<long long> v;
    istringstream iss(line);
    long long x;
    while (iss >> x) v.push_back(x);
    return v;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire stdin
    std::string all;
    {
        std::ostringstream ss;
        ss << cin.rdbuf();
        all = ss.str();
    }
    if (all.empty()) return 0;

    // Determine mode by first non-space char
    size_t pos = 0;
    while (pos < all.size() && is_space(all[pos])) pos++;
    if (pos == all.size()) return 0;

    if (all[pos] == '0' || all[pos] == '1') {
        // Transcript-only mode: compute responses based on final guess (best effort).
        // Parse lines and find the last guess to determine n and hidden permutation.
        vector<string> lines = split_lines(all);
        vector<long long> hidden_ll;
        int n = 0;

        for (const auto &ln : lines) {
            auto toks = parse_ints_from_line(ln);
            if (!toks.empty() && toks[0] == 1) {
                hidden_ll = toks;
            }
        }
        if (!hidden_ll.empty()) {
            // hidden_ll[0] == 1, rest is permutation
            n = (int)hidden_ll.size() - 1;
        } else {
            // Cannot determine hidden; nothing useful to output.
            return 0;
        }
        vector<int> hidden(n);
        for (int i = 0; i < n; ++i) hidden[i] = (int)hidden_ll[i + 1];

        for (const auto &ln : lines) {
            auto toks = parse_ints_from_line(ln);
            if (toks.empty()) continue;
            if (toks[0] == 0) {
                if ((int)toks.size() < 1 + n) {
                    // Malformed query; skip or output 0
                    cout << 0 << "\n";
                    continue;
                }
                int match = 0;
                for (int i = 0; i < n; ++i) {
                    if ((int)toks[i + 1] == hidden[i]) match++;
                }
                cout << match << "\n";
            } else if (toks[0] == 1) {
                // Final guess line; no output, end
                // But keep processing if more lines? Typically stop.
                // We'll stop here to mirror interactive behavior.
                break;
            }
        }
        return 0;
    } else {
        // Offline interactor mode: input is n followed by hidden permutation, then sequence of commands.
        // If hidden permutation is not present, print a trivial guess and exit.
        // Parse all ints from the entire input
        vector<long long> nums;
        nums.reserve(1 << 16);
        {
            istringstream iss(all);
            long long x;
            while (iss >> x) nums.push_back(x);
        }
        if (nums.empty()) return 0;
        size_t idx = 0;
        long long nll = nums[idx++];
        if (nll <= 0 || nll > 1000000) {
            // Invalid n; nothing to do
            return 0;
        }
        int n = (int)nll;
        vector<int> hidden(n);
        bool hasHidden = true;
        if (idx + (size_t)n <= nums.size()) {
            for (int i = 0; i < n; ++i) hidden[i] = (int)nums[idx++];
        } else {
            hasHidden = false;
        }
        if (!hasHidden) {
            // No hidden provided; output a trivial guess and exit
            cout << 1;
            for (int i = 1; i <= n; ++i) cout << " " << i;
            cout << "\n";
            return 0;
        }
        // Process commands (t, then n numbers)
        while (idx < nums.size()) {
            long long t = nums[idx++];
            if (t == 0) {
                if (idx + (size_t)n > nums.size()) break;
                int match = 0;
                for (int i = 0; i < n; ++i) {
                    int qv = (int)nums[idx++];
                    if (qv == hidden[i]) match++;
                }
                cout << match << "\n";
            } else if (t == 1) {
                // Read guess and terminate
                if (idx + (size_t)n > nums.size()) break;
                // Consume guess
                idx += n;
                break;
            } else {
                // Unknown command; cannot proceed safely
                break;
            }
        }
        return 0;
    }
}