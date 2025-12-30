#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char readChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = readChar();
        }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
    }
};

struct FastOutput {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0;

    ~FastOutput() { flush(); }

    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }

    inline void writeChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }

    inline void writeStr(const char *s) {
        while (*s) writeChar(*s++);
    }

    template <class T>
    inline void writeInt(T x, char endc = 0) {
        if (x == 0) {
            writeChar('0');
            if (endc) writeChar(endc);
            return;
        }
        if constexpr (is_signed<T>::value) {
            if (x < 0) {
                writeChar('-');
                x = -x;
            }
        }
        char s[32];
        int n = 0;
        while (x > 0) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        while (n--) writeChar(s[n]);
        if (endc) writeChar(endc);
    }
};

struct Fenwick {
    int n = 0;
    vector<int> bit;

    Fenwick() {}
    explicit Fenwick(int n_) { init(n_); }

    void init(int n_) {
        n = n_;
        bit.assign(n + 1, 0);
    }

    void initOnes(int n_) {
        n = n_;
        bit.assign(n + 1, 0);
        for (int i = 1; i <= n; i++) bit[i] = (i & -i);
    }

    inline void add(int i, int delta) {
        for (; i <= n; i += i & -i) bit[i] += delta;
    }

    inline int sumPrefix(int i) const {
        int s = 0;
        for (; i > 0; i -= i & -i) s += bit[i];
        return s;
    }
};

struct Candidate {
    unsigned long long final_cost = ULLONG_MAX;
    long long total_cost = 0;
    int moves_count = 0;
    vector<pair<int,int>> moves;
};

static inline bool better(const Candidate &a, const Candidate &b) {
    if (a.final_cost != b.final_cost) return a.final_cost < b.final_cost;
    if (a.moves_count != b.moves_count) return a.moves_count < b.moves_count;
    return a.total_cost < b.total_cost;
}

Candidate candidate_front_suffix(const vector<int>& pos) {
    int n = (int)pos.size() - 1;
    int s = n;
    while (s > 1 && pos[s - 1] < pos[s]) s--;
    int k = s - 1;

    Candidate c;
    c.moves.reserve(k);
    c.moves_count = k;
    c.total_cost = k;
    unsigned long long t = (unsigned long long)(k + 1);
    c.final_cost = t * t;

    Fenwick fw(n);
    fw.init(n);
    int moved = 0;

    for (int val = k; val >= 1; --val) {
        int p = pos[val];
        int le = fw.sumPrefix(p);
        int after = moved - le;
        int x = p + after;
        c.moves.push_back({x, 1});
        fw.add(p, 1);
        moved++;
    }
    return c;
}

Candidate candidate_fix_left(const vector<int>& pos) {
    int n = (int)pos.size() - 1;
    Candidate c;
    c.moves.reserve(n);
    long long total = 0;

    Fenwick fw;
    fw.initOnes(n);

    for (int i = 1; i <= n; i++) {
        int p = pos[i];
        int r = fw.sumPrefix(p);          // rank among remaining
        int x = (i - 1) + r;              // position in full array
        if (x != i) {
            c.moves.push_back({x, i});
            total += i;
        }
        fw.add(p, -1);                    // remove i from remaining
    }

    c.moves_count = (int)c.moves.size();
    c.total_cost = total;
    c.final_cost = (unsigned long long)(total + 1) * (unsigned long long)(c.moves_count + 1);
    return c;
}

Candidate candidate_fix_right(const vector<int>& pos) {
    int n = (int)pos.size() - 1;
    Candidate c;
    c.moves.reserve(n);
    long long total = 0;

    Fenwick fw;
    fw.initOnes(n);

    for (int i = n; i >= 1; i--) {
        int p = pos[i];
        int x = fw.sumPrefix(p);          // position among remaining (front block)
        if (x != i) {
            c.moves.push_back({x, i});
            total += i;
        }
        fw.add(p, -1);                    // remove i from remaining
    }

    c.moves_count = (int)c.moves.size();
    c.total_cost = total;
    c.final_cost = (unsigned long long)(total + 1) * (unsigned long long)(c.moves_count + 1);
    return c;
}

int main() {
    FastScanner fs;
    int n;
    if (!fs.readInt(n)) return 0;

    vector<int> pos(n + 1);
    for (int i = 1; i <= n; i++) {
        int x; fs.readInt(x);
        pos[x] = i;
    }

    Candidate best;

    Candidate a = candidate_front_suffix(pos);
    best = a;

    Candidate l = candidate_fix_left(pos);
    if (better(l, best)) best = std::move(l);

    Candidate r = candidate_fix_right(pos);
    if (better(r, best)) best = std::move(r);

    FastOutput out;
    out.writeInt(best.final_cost, ' ');
    out.writeInt(best.moves_count, '\n');
    for (auto &mv : best.moves) {
        out.writeInt(mv.first, ' ');
        out.writeInt(mv.second, '\n');
    }
    return 0;
}