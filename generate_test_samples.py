def make_sequence(gc_percent, length=20):
    gc_count = round(length * gc_percent / 100)
    at_count = length - gc_count
    gc_bases = ('GC' * gc_count)[:gc_count]
    at_bases = ('AT' * at_count)[:at_count]
    seq = ''
    gi, ai = 0, 0
    for i in range(length):
        if gi < len(gc_bases) and (ai >= len(at_bases) or i % 2 == 0):
            seq += gc_bases[gi]; gi += 1
        else:
            seq += at_bases[ai]; ai += 1
    return seq

def make_fastq(sample_id, reads_config):
    lines = []
    for i, (gc, length, qual) in enumerate(reads_config, 1):
        seq = make_sequence(gc, length)
        actual_gc = round((seq.count('G') + seq.count('C')) / length * 100, 1)
        print(f"  Read {i}: {seq} | GC={actual_gc}%")
        lines.append(f"@{sample_id}_READ{i} length={length}")
        lines.append(seq)
        lines.append("+")
        lines.append(qual * length)
    return '\n'.join(lines)

samples = {
    'sample_003': [(50, 20, 'I'), (50, 20, 'H'), (50, 20, 'G')],
    'sample_004': [(65, 20, 'I'), (65, 20, 'H'), (65, 20, 'G')],
    'sample_005': [(35, 20, 'I'), (35, 20, 'H'), (35, 20, 'G')],
    'sample_006': [(55, 20, 'I'), (55, 20, 'H'), (55, 20, 'G')],
}

for sample_id, config in samples.items():
    print(f"\n{sample_id}:")
    content = make_fastq(sample_id, config)
    filename = f"layer2-lambda-validation/test-data/{sample_id}.fastq"
    with open(filename, 'w') as f:
        f.write(content)
    print(f"  Written to {filename}")

print("\nDone!")
EOF

