def toJson(article_list) {
    def json = groovy.json.JsonOutput.toJson(article_list)
    json = groovy.json.JsonOutput.prettyPrint(json)
    def tempFile = File.createTempFile("articles_", ".json")
    tempFile.write(json)
    return file(tempFile)
}

def batchFlattened(channel, batch_size) {
    return channel
        .buffer(size: batch_size, remainder: true)
        .map { batch -> toJson(batch) }
        .take(2)
}

def batchArticles(channel, batch_size) {
    return channel
        .splitJson()
        .flatten()
        .buffer(size: batch_size, remainder: true)
        .map { batch -> toJson(batch) }
        .take(2)
}

def filterAndBatch(channel, batch_size, key, value) {

    if (!key || !value) {
        error "Both key and value must be provided for filtering."
    }

    def branches = channel
        .splitJson()
        .flatten()
        .branch {
            match: it[key] == value
            no_match: it[key] != value
        }

    return [
        match: batchFlattened(branches.match, batch_size),
        no_match: batchFlattened(branches.no_match, batch_size)
    ]
}
