#include <bits/stdc++.h>
using namespace std;

struct Op {
    int type; // 1=query, 2=swap, 3=final
    int a, b; // l,r or i,j
    int id;   // query index
    vector<int> p; // for final permutation
    Op(): type(0), a(0), b(0), id(-1) {}
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<Op> ops;
    vector<int> p_final;
    string line;
    int queryCount = 0, swapCount = 0;
    
    vector<vector<long long>> allTokens;
    vector<long long> flatTokens;
    vector<string> lines;
    
    while (true) {
        string s;
        if (!getline(cin, s)) break;
        if (!s.empty() && s.back() == '\r') s.pop_back();
        lines.push_back(s);
    }
    for (auto &s : lines) {
        bool allspace = true;
        for (char c : s) if (!isspace((unsigned char)c)) { allspace = false; break; }
        if (allspace) continue;
        stringstream ss(s);
        vector<long long> toks;
        long long x;
        while (ss >> x) toks.push_back(x);
        if (toks.empty()) continue;
        allTokens.push_back(toks);
    }
    
    for (auto &toks : allTokens) {
        long long t = toks[0];
        if (t == 1) {
            if (toks.size() >= 3) {
                Op op;
                op.type = 1;
                op.a = (int)toks[1];
                op.b = (int)toks[2];
                op.id = queryCount++;
                ops.push_back(op);
            }
        } else if (t == 2) {
            if (toks.size() >= 3) {
                Op op;
                op.type = 2;
                op.a = (int)toks[1];
                op.b = (int)toks[2];
                ops.push_back(op);
                swapCount++;
            }
        } else if (t == 3) {
            Op op;
            op.type = 3;
            op.p.clear();
            for (size_t i = 1; i < toks.size(); i++) op.p.push_back((int)toks[i]);
            p_final = op.p;
            ops.push_back(op);
        } else {
            // ignore unknown lines
        }
    }
    
    if (p_final.empty()) {
        // No final permutation found; nothing to output
        return 0;
    }
    
    int n = (int)p_final.size();
    vector<int> Pcurr = p_final;
    vector<int> pos(n + 1, 0);
    for (int i = 0; i < n; ++i) pos[Pcurr[i]] = i + 1;
    
    vector<int> answers(queryCount, 0);
    for (int idx = (int)ops.size() - 1; idx >= 0; --idx) {
        Op &op = ops[idx];
        if (op.type == 1) {
            int l = op.a, r = op.b;
            int cnt = 0;
            for (int x = 1; x < n; ++x) {
                int px = pos[x];
                int py = pos[x + 1];
                if (px >= l && px <= r && py >= l && py <= r) cnt++;
            }
            int seg = (r - l + 1) - cnt;
            answers[op.id] = seg;
        } else if (op.type == 2) {
            int i = op.a, j = op.b;
            int vi = Pcurr[i - 1];
            int vj = Pcurr[j - 1];
            swap(Pcurr[i - 1], Pcurr[j - 1]);
            pos[vi] = j;
            pos[vj] = i;
        } else if (op.type == 3) {
            // do nothing
        }
    }
    
    cout << n << " " << 100 << " " << 50 << "\n";
    for (int i = 0; i < queryCount; ++i) {
        cout << answers[i] << "\n";
    }
    return 0;
}