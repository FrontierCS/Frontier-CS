#include <bits/stdc++.h>
using namespace std;

static inline bool is_number(const string& s){
    if(s.empty()) return false;
    size_t i = 0;
    if(s[0] == '-' || s[0] == '+') i = 1;
    if(i >= s.size()) return false;
    for(; i < s.size(); ++i){
        if(!isdigit((unsigned char)s[i])) return false;
    }
    return true;
}

static vector<string> split_ws(const string& s){
    vector<string> res;
    string token;
    istringstream iss(s);
    while(iss >> token) res.push_back(token);
    return res;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<string> lines;
    string line;
    while(true){
        string tmp;
        if(!getline(cin, tmp)) break;
        lines.push_back(tmp);
    }

    // Remove empty lines
    vector<string> nonempty;
    for(auto &l: lines){
        bool allspace = true;
        for(char c: l) if(!isspace((unsigned char)c)){ allspace = false; break; }
        if(!allspace) nonempty.push_back(l);
    }
    lines.swap(nonempty);

    if(lines.empty()){
        return 0;
    }

    // Case 1: single line with n or with n and permutation
    if(lines.size() == 1){
        vector<string> toks = split_ws(lines[0]);
        if(toks.empty()){
            return 0;
        }
        if(is_number(toks[0])){
            int n = stoi(toks[0]);
            if((int)toks.size() >= n + 1){
                // Assume permutation provided inline
                cout << 1;
                for(int i = 1; i <= n; ++i){
                    cout << ' ' << toks[i];
                }
                cout << '\n';
                return 0;
            } else {
                // No more info; output identity guess
                cout << 1;
                for(int i = 1; i <= n; ++i){
                    cout << ' ' << i;
                }
                cout << '\n';
                return 0;
            }
        } else {
            // Unknown format; do nothing
            return 0;
        }
    }

    // Detect if this looks like "conversation log" mode:
    bool conv_mode = true;
    for(auto &l: lines){
        vector<string> toks = split_ws(l);
        if(toks.empty()){ continue; }
        if(!(toks[0] == "0" || toks[0] == "1")){
            conv_mode = false;
            break;
        }
    }

    if(conv_mode){
        // Determine n from lines (max tokens per line minus 1)
        int n = 0;
        for(auto &l: lines){
            auto toks = split_ws(l);
            if(toks.size() >= 2) n = max(n, (int)toks.size() - 1);
        }
        // Find last line starting with '1' as hidden permutation
        vector<int> p;
        for(int i = (int)lines.size()-1; i >= 0; --i){
            auto toks = split_ws(lines[i]);
            if(toks.empty()) continue;
            if(toks[0] == "1" && (int)toks.size() >= 2){
                int m = (int)toks.size() - 1;
                p.assign(m, 0);
                bool ok = true;
                for(int j = 0; j < m; ++j){
                    if(!is_number(toks[j+1])) { ok = false; break; }
                    p[j] = stoi(toks[j+1]);
                }
                if(ok){
                    n = max(n, (int)p.size());
                    break;
                }
            }
        }
        if(p.empty()){
            // Fallback: identity permutation of length n
            if(n <= 0) n = 1;
            p.resize(n);
            iota(p.begin(), p.end(), 1);
        }

        // Answer counts for each '0' line; ignore '1' lines for output
        for(auto &l: lines){
            auto toks = split_ws(l);
            if(toks.empty()) continue;
            if(!(toks[0] == "0" || toks[0] == "1")) continue;
            vector<int> q;
            for(size_t i = 1; i < toks.size(); ++i){
                if(is_number(toks[i])) q.push_back(stoi(toks[i]));
                else q.push_back(0);
            }
            int m = min((int)q.size(), (int)p.size());
            int cnt = 0;
            for(int i = 0; i < m; ++i){
                if(q[i] == p[i]) ++cnt;
            }
            if(toks[0] == "0"){
                cout << cnt << '\n';
            }
        }
        return 0;
    }

    // Otherwise, try to parse: first token is n, followed by permutation either on same or next line(s)
    vector<string> all_toks;
    for(auto &l: lines){
        auto toks = split_ws(l);
        for(auto &t: toks) all_toks.push_back(t);
    }
    if(all_toks.empty()) return 0;
    if(!is_number(all_toks[0])) return 0;
    int n = stoi(all_toks[0]);
    if((int)all_toks.size() >= n + 1){
        cout << 1;
        for(int i = 1; i <= n; ++i){
            cout << ' ' << all_toks[i];
        }
        cout << '\n';
        return 0;
    } else {
        // Fallback: identity guess
        cout << 1;
        for(int i = 1; i <= n; ++i){
            cout << ' ' << i;
        }
        cout << '\n';
        return 0;
    }
}