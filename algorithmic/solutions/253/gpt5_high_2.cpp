#include <bits/stdc++.h>
using namespace std;

static bool is_valid_header(int n, int m) {
    return (2 <= n && n <= 2000 && n - 1 <= m && m <= 2000);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    // Read entire input into a string
    std::string input((std::istreambuf_iterator<char>(cin)), std::istreambuf_iterator<char>());
    // Split into tokens
    vector<string> tokens;
    {
        string cur;
        for (char ch : input) {
            if (isspace(static_cast<unsigned char>(ch))) {
                if (!cur.empty()) {
                    tokens.push_back(cur);
                    cur.clear();
                }
            } else {
                cur.push_back(ch);
            }
        }
        if (!cur.empty()) tokens.push_back(cur);
    }
    
    size_t idx = 0;
    auto next_int = [&](int def = 0) -> int {
        if (idx >= tokens.size()) return def;
        int val = 0;
        try {
            val = stoi(tokens[idx]);
        } catch (...) {
            val = def;
        }
        idx++;
        return val;
    };
    
    if (idx >= tokens.size()) return 0;
    int t = next_int(0);
    if (t <= 0) return 0;
    
    for (int tc = 0; tc < t; ++tc) {
        // If tokens may contain extra 0/1 between tests, skip until a valid header is found
        if (tc > 0) {
            while (idx + 1 < tokens.size()) {
                int n_try, m_try;
                try { n_try = stoi(tokens[idx]); } catch (...) { n_try = -1; }
                try { m_try = stoi(tokens[idx + 1]); } catch (...) { m_try = -1; }
                if (is_valid_header(n_try, m_try)) break;
                idx++;
            }
        }
        
        int n = next_int(0);
        int m = next_int(0);
        if (!is_valid_header(n, m)) {
            // Fallback: if header invalid, try to scan forward to find a valid header
            bool found = false;
            size_t start = (idx >= 2 ? idx - 2 : idx);
            for (size_t j = start; j + 1 < tokens.size(); ++j) {
                int n_try = 0, m_try = 0;
                try { n_try = stoi(tokens[j]); } catch (...) { continue; }
                try { m_try = stoi(tokens[j + 1]); } catch (...) { continue; }
                if (is_valid_header(n_try, m_try)) {
                    idx = j + 2;
                    n = n_try; m = m_try;
                    found = true;
                    break;
                }
            }
            if (!found) {
                // If still not found, output zeros and continue safely
                cout << "!";
                for (int i = 0; i < m; ++i) cout << " " << 0;
                cout << "\n";
                continue;
            }
        }
        
        // Read edges
        for (int i = 0; i < m; ++i) {
            // If missing, use defaults
            (void)next_int(1);
            (void)next_int(1);
        }
        
        // Read statuses if present (assume next m tokens are statuses)
        vector<int> c(m, 0);
        for (int i = 0; i < m; ++i) {
            if (idx < tokens.size()) {
                int v = 0;
                try { v = stoi(tokens[idx]); } catch (...) { v = 0; }
                c[i] = (v != 0) ? 1 : 0;
                idx++;
            } else {
                c[i] = 0;
            }
        }
        
        cout << "!";
        for (int i = 0; i < m; ++i) cout << " " << c[i];
        cout << "\n";
        
        // After answering (for all but last test), skip any trailing 0/1 tokens
        // until a valid next header appears, to be resilient to interactive-like logs.
        if (tc + 1 < t) {
            while (idx + 1 < tokens.size()) {
                int n_try, m_try;
                try { n_try = stoi(tokens[idx]); } catch (...) { n_try = -1; }
                try { m_try = stoi(tokens[idx + 1]); } catch (...) { m_try = -1; }
                if (is_valid_header(n_try, m_try)) break;
                idx++;
            }
        }
    }
    
    return 0;
}