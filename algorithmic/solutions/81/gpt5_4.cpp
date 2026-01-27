#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;

    string bits;
    bits.reserve(N);

    // Try to read the string S (consisting of '0' and '1') from the remaining input
    char ch;
    if (cin.peek() == '\n' || cin.peek() == '\r') cin.get(ch); // consume possible newline after N
    while ((int)bits.size() < N && cin.get(ch)) {
        if (ch == '0' || ch == '1') bits.push_back(ch);
    }
    if ((int)bits.size() < N) {
        string token;
        while ((int)bits.size() < N && (cin >> token)) {
            for (char c : token) {
                if (c == '0' || c == '1') bits.push_back(c);
                if ((int)bits.size() == N) break;
            }
        }
    }
    if ((int)bits.size() > N) bits.resize(N);
    if ((int)bits.size() < N) bits.resize(N, '0'); // fallback if not enough bits are provided

    cout << "0\n" << bits << "\n";
    return 0;
}