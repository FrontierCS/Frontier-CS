#include <bits/stdc++.h>
using namespace std;

int ask(const vector<int>& indices) {
    cout << "0 " << indices.size();
    for (int x : indices) cout << " " << x;
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
}

void answer(const string& s) {
    cout << "1 " << s << endl;
    cout.flush();
}

int main() {
    int n;
    cin >> n;
    
    const int L = 500;          // large repetition count
    int queries_used = 0;
    int p = -1, q = -1;         // p = '(', q = ')'

    // Try to find a pair among the first few indices
    for (int i = 1; i <= min(10, n) && p == -1; ++i) {
        for (int j = i + 1; j <= min(i + 10, n) && p == -1; ++j) {
            if (queries_used >= 200) break;
            
            vector<int> q1;
            for (int t = 0; t < L; ++t) q1.push_back(i);
            for (int t = 0; t < L; ++t) q1.push_back(j);
            int f1 = ask(q1);
            ++queries_used;
            if (f1 == L) {
                p = i; q = j;
                break;
            }

            if (queries_used >= 200) break;
            vector<int> q2;
            for (int t = 0; t < L; ++t) q2.push_back(j);
            for (int t = 0; t < L; ++t) q2.push_back(i);
            int f2 = ask(q2);
            ++queries_used;
            if (f2 == L) {
                p = j; q = i;
                break;
            }
        }
    }

    // If no pair found, assume index 1 is '(' and try to find a ')'
    if (p == -1) {
        p = 1;
        for (int j = 2; j <= n && q == -1; ++j) {
            if (queries_used >= 200) break;
            vector<int> qry;
            for (int t = 0; t < L; ++t) qry.push_back(p);
            qry.push_back(j);
            int f = ask(qry);
            ++queries_used;
            if (f == 1) {
                q = j;
                break;
            }
        }
        // If still no ')', guess all '('
        if (q == -1) {
            answer(string(n, '('));
            return 0;
        }
    }

    string ans(n, '?');
    ans[p - 1] = '(';
    ans[q - 1] = ')';

    // Determine the rest using p as known '('
    for (int i = 1; i <= n; ++i) {
        if (i == p || i == q) continue;
        if (queries_used >= 200) {
            ans[i - 1] = '(';   // guess when out of queries
            continue;
        }
        vector<int> qry;
        for (int t = 0; t < L; ++t) qry.push_back(p);
        qry.push_back(i);
        int f = ask(qry);
        ++queries_used;
        ans[i - 1] = (f == 1 ? ')' : '(');
    }

    answer(ans);
    return 0;
}