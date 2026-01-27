#include <bits/stdc++.h>
using namespace std;

static inline int cid(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    return 10 + (c - 'A');
}

struct Index {
    vector<int> pos;   // concatenated positions grouped by character
    int start[37];     // start offsets for each character group (0..36)
};

static Index buildIndex(const string &B) {
    Index idx;
    int freq[36] = {0};

    const char *bp = B.data();
    const char *be = bp + B.size();
    for (const char *p = bp; p < be; ++p) ++freq[cid(*p)];

    idx.start[0] = 0;
    for (int k = 0; k < 36; ++k) idx.start[k + 1] = idx.start[k] + freq[k];

    idx.pos.resize(B.size());
    int ptr[36];
    for (int k = 0; k < 36; ++k) ptr[k] = idx.start[k];

    for (int i = 0, n = (int)B.size(); i < n; ++i) {
        int k = cid(B[i]);
        idx.pos[ptr[k]++] = i;
    }
    return idx;
}

static string greedyForward(const string &A, const Index &idx, int Bsize) {
    string out;
    out.reserve((size_t)min<int>((int)A.size(), Bsize));

    int ptr[36];
    for (int k = 0; k < 36; ++k) ptr[k] = idx.start[k];

    int cur = -1;
    const char *ap = A.data();
    const char *ae = ap + A.size();
    for (const char *p = ap; p < ae; ++p) {
        int k = cid(*p);
        int &pi = ptr[k];
        int e = idx.start[k + 1];
        while (pi < e && idx.pos[pi] <= cur) ++pi;
        if (pi < e) {
            out.push_back(*p);
            cur = idx.pos[pi];
            ++pi;
        }
    }
    return out;
}

static string greedyReverse(const string &A, const Index &idx, int Bsize) {
    string out;
    out.reserve((size_t)min<int>((int)A.size(), Bsize));

    int ptr[36];
    for (int k = 0; k < 36; ++k) ptr[k] = idx.start[k + 1] - 1;

    int cur = Bsize;
    for (int i = (int)A.size() - 1; i >= 0; --i) {
        char c = A[i];
        int k = cid(c);
        int &pi = ptr[k];
        int s = idx.start[k];
        while (pi >= s && idx.pos[pi] >= cur) --pi;
        if (pi >= s) {
            out.push_back(c);
            cur = idx.pos[pi];
            --pi;
        }
    }
    reverse(out.begin(), out.end());
    return out;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) s2.clear();

    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    const string *A = &s1, *B = &s2;
    if (A->size() > B->size()) swap(A, B);

    Index idx = buildIndex(*B);
    int Bsize = (int)B->size();

    string best = greedyForward(*A, idx, Bsize);
    string cand = greedyReverse(*A, idx, Bsize);
    if (cand.size() > best.size()) best = std::move(cand);

    cout.write(best.data(), (streamsize)best.size());
    cout.put('\n');
    return 0;
}