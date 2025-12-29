#include <bits/stdc++.h>
using namespace std;

static void flush_out() { cout.flush(); }

static string ask_set(const vector<int>& elems) {
    cout << "? " << elems.size();
    for (int v : elems) cout << ' ' << v;
    cout << '\n';
    flush_out();
    string resp;
    if (!(cin >> resp)) exit(0);
    return resp;
}

static string make_guess(int g) {
    cout << "! " << g << '\n';
    flush_out();
    string resp;
    if (!(cin >> resp)) exit(0);
    return resp;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        string r = make_guess(1);
        return 0;
    }

    vector<int> T, L;
    T.reserve(n);
    for (int i = 1; i <= n; i++) T.push_back(i);

    vector<int> mark(n + 1, 0);
    int stamp = 1;

    int queries = 0;

    while (queries < 53) {
        int t = (int)T.size();
        int l = (int)L.size();
        int u = t + l;
        if (u <= 2) break;

        int total = u / 2;       // floor(u/2), guaranteed >= 1 when u > 2
        int takeL = l / 2;       // floor(l/2)
        int takeT = total - takeL;

        vector<int> S;
        S.reserve(total);

        for (int i = 0; i < takeL; i++) {
            int v = L[i];
            mark[v] = stamp;
            S.push_back(v);
        }
        for (int i = 0; i < takeT; i++) {
            int v = T[i];
            mark[v] = stamp;
            S.push_back(v);
        }

        string ans = ask_set(S);
        queries++;

        vector<int> newT, newL;
        newT.reserve((u + 1) / 2);
        newL.reserve(u);

        if (ans == "YES") {
            // newT = (T in S) + (L in S)
            // newL = (T not in S)
            for (int v : T) {
                if (mark[v] == stamp) newT.push_back(v);
                else newL.push_back(v);
            }
            for (int v : L) {
                if (mark[v] == stamp) newT.push_back(v);
            }
        } else { // "NO"
            // newT = (T not in S) + (L not in S)
            // newL = (T in S)
            for (int v : T) {
                if (mark[v] == stamp) newL.push_back(v);
                else newT.push_back(v);
            }
            for (int v : L) {
                if (mark[v] != stamp) newT.push_back(v);
            }
        }

        T.swap(newT);
        L.swap(newL);
        stamp++;
        if (stamp == INT_MAX) {
            fill(mark.begin(), mark.end(), 0);
            stamp = 1;
        }
    }

    vector<int> cand;
    cand.reserve(T.size() + L.size());
    for (int v : T) cand.push_back(v);
    for (int v : L) cand.push_back(v);

    if (cand.empty()) cand.push_back(1);

    int guesses = 0;
    for (int i = 0; i < (int)cand.size() && guesses < 2; i++) {
        string r = make_guess(cand[i]);
        guesses++;
        if (r == ":)") return 0;
    }

    return 0;
}