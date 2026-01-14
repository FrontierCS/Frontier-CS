#include <bits/stdc++.h>
using namespace std;

static vector<int> findLISIndices(const vector<int>& perm, const vector<char>& used, bool decreasing) {
    int n = (int)perm.size();
    vector<int> prev(n, -1);
    vector<int> tailsKey;
    vector<int> tailsIdx;
    tailsKey.reserve(n);
    tailsIdx.reserve(n);

    for (int i = 0; i < n; i++) {
        if (used[i]) continue;
        int key = decreasing ? -perm[i] : perm[i];

        auto it = lower_bound(tailsKey.begin(), tailsKey.end(), key);
        int pos = (int)(it - tailsKey.begin());

        if (pos > 0) prev[i] = tailsIdx[pos - 1];

        if (pos == (int)tailsKey.size()) {
            tailsKey.push_back(key);
            tailsIdx.push_back(i);
        } else {
            tailsKey[pos] = key;
            tailsIdx[pos] = i;
        }
    }

    if (tailsIdx.empty()) return {};
    int idx = tailsIdx.back();
    vector<int> res;
    while (idx != -1) {
        res.push_back(idx);
        idx = prev[idx];
    }
    reverse(res.begin(), res.end());
    return res;
}

static void printVec(const vector<int>& v) {
    for (int i = 0; i < (int)v.size(); i++) {
        if (i) cout << ' ';
        cout << v[i];
    }
    cout << "\n";
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> perm(n);
    for (int i = 0; i < n; i++) cin >> perm[i];

    vector<char> usedA(n, 0);
    vector<int> Acore = findLISIndices(perm, usedA, false);
    for (int idx : Acore) usedA[idx] = 1;
    int baseA = (int)Acore.size();

    vector<int> bestB, bestC, bestD;
    long long bestScore = -1;

    // Orders for extracting (two DEC, one INC) from remaining after reserving Acore
    // Represent as 0=DEC, 1=INC
    vector<array<int,3>> orders = {
        array<int,3>{0,1,0},
        array<int,3>{1,0,0},
        array<int,3>{0,0,1}
    };

    for (auto ord : orders) {
        vector<char> used = usedA;
        vector<int> B, C, D;
        bool firstDec = true;

        for (int t = 0; t < 3; t++) {
            if (ord[t] == 1) {
                if (!C.empty()) continue; // only one INC slot
                C = findLISIndices(perm, used, false);
                for (int idx : C) used[idx] = 1;
            } else {
                vector<int> decSeq = findLISIndices(perm, used, true);
                for (int idx : decSeq) used[idx] = 1;
                if (firstDec) {
                    B = std::move(decSeq);
                    firstDec = false;
                } else {
                    D = std::move(decSeq);
                }
            }
        }

        long long score = (long long)baseA + (long long)B.size() + (long long)C.size() + (long long)D.size();
        if (score > bestScore) {
            bestScore = score;
            bestB = std::move(B);
            bestC = std::move(C);
            bestD = std::move(D);
        }
    }

    vector<int> group(n, 0); // 0=A, 1=B, 2=C, 3=D
    for (int idx : bestB) group[idx] = 1;
    for (int idx : bestC) group[idx] = 2;
    for (int idx : bestD) group[idx] = 3;

    vector<int> A, B, C, D;
    A.reserve(n);
    B.reserve(bestB.size());
    C.reserve(bestC.size());
    D.reserve(bestD.size());

    for (int i = 0; i < n; i++) {
        if (group[i] == 0) A.push_back(perm[i]);
        else if (group[i] == 1) B.push_back(perm[i]);
        else if (group[i] == 2) C.push_back(perm[i]);
        else D.push_back(perm[i]);
    }

    cout << A.size() << " " << B.size() << " " << C.size() << " " << D.size() << "\n";
    printVec(A);
    printVec(B);
    printVec(C);
    printVec(D);

    return 0;
}