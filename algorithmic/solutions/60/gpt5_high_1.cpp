#include <bits/stdc++.h>
using namespace std;

long long parseLL(const string &s) {
    try {
        size_t idx = 0;
        long long val = stoll(s, &idx);
        if (idx == s.size()) return val;
    } catch (...) {}
    try {
        long double d = stold(s);
        return llround(d);
    } catch (...) {
        return 0;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<string> tokens;
    string s;
    while (cin >> s) tokens.push_back(s);
    if (tokens.size() < 3) return 0;
    
    long long x = parseLL(tokens[0]);
    long long y = parseLL(tokens[1]);
    long long r = parseLL(tokens[2]);
    
    cout << "answer " << x << " " << y << " " << r << "\n";
    return 0;
}