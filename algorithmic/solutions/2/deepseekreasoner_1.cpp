#include <iostream>
#include <vector>
#include <set>

using namespace std;

int ask(const vector<int>& q) {
    cout << "0";
    for (size_t i = 1; i < q.size(); ++i) {
        cout << " " << q[i];
    }
    cout << endl;
    cout.flush();
    int response;
    cin >> response;
    return response;
}

void guess(const vector<int>& ans) {
    cout << "1";
    for (size_t i = 1; i < ans.size(); ++i) {
        cout << " " << ans[i];
    }
    cout << endl;
    cout.flush();
}

int main() {
    int n;
    cin >> n;

    vector<int> ans(n + 1, 0);
    if (n == 1) {
        cout << "1 1" << endl;
        return 0;
    }
    if (n == 2) {
        vector<int> q1 = {0, 1, 1};
        int r1 = ask(q1);
        vector<int> q2 = {0, 1, 2};
        int r2 = ask(q2);
        if (r2 == 2) {
            ans[1] = 1; ans[2] = 2;
        } else {
            ans[1] = 2; ans[2] = 1;
        }
        guess(ans);
        return 0;
    }

    vector<int> undet;
    for (int i = 1; i <= n; ++i) undet.push_back(i);
    set<int> detPos;

    for (int v = 1; v <= n; ++v) {
        if (undet.empty()) break;
        if (v == 1) {
            int L = 0, R = undet.size() - 1;
            while (L < R) {
                int mid = (L + R) / 2;
                int a = 1, b = 2;
                if (a == v) a = 2;
                b = a + 1;
                if (b == v) ++b;
                if (b > n) {
                    b = 1;
                    if (b == v) ++b;
                    if (b == a) ++b;
                }
                vector<int> qA(n + 1, 0);
                for (int i = L; i <= mid; ++i) qA[undet[i]] = v;
                for (int i = mid + 1; i <= R; ++i) qA[undet[i]] = a;
                int rA = ask(qA);

                vector<int> qB(n + 1, 0);
                for (int i = L; i <= mid; ++i) qB[undet[i]] = v;
                for (int i = mid + 1; i <= R; ++i) qB[undet[i]] = b;
                int rB = ask(qB);

                int X;
                if (rA == rB) X = rA;
                else if (rA == rB + 1) X = rA - 1;
                else if (rA + 1 == rB) X = rB - 1;
                else {
                    if (rA > rB) X = rA - 1;
                    else X = rB - 1;
                }
                if (X == 1) R = mid;
                else L = mid + 1;
            }
            int pos = undet[L];
            ans[pos] = v;
            undet.erase(undet.begin() + L);
            detPos.insert(pos);
        } else {
            int f = ans[*detPos.begin()];
            int L = 0, R = undet.size() - 1;
            while (L < R) {
                int mid = (L + R) / 2;
                vector<int> q(n + 1, 0);
                for (int p : detPos) q[p] = ans[p];
                for (int i = L; i <= mid; ++i) q[undet[i]] = v;
                for (int i = mid + 1; i <= R; ++i) q[undet[i]] = f;
                int r = ask(q);
                int D = detPos.size();
                if (r == D + 1) R = mid;
                else L = mid + 1;
            }
            int pos = undet[L];
            ans[pos] = v;
            undet.erase(undet.begin() + L);
            detPos.insert(pos);
        }
    }

    guess(ans);
    return 0;
}